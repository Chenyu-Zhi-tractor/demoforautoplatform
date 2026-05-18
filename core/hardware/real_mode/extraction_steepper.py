import time
import serial

DEFAULT_PORT = "COM9"
BAUD_RATE = 115200
STEPS_PER_REVOLUTION = 400  # Must match firmware configuration


class ExtractionStepperController:
    """
    Dual stepper controller (single Mega board, one COM port).
    Axis A -> STIR, Axis B -> SWITCH.
    """

    def __init__(self, port=DEFAULT_PORT, baudrate=BAUD_RATE):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self._logger = print
        self.commands_log = []

    def set_logger(self, logger_func):
        self._logger = logger_func

    def _log(self, msg):
        if self._logger:
            self._logger(msg)

    def _open_serial(self):
        # Single Mega board handles both motors over one COM port
        if self.ser is None or not self.ser.is_open:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(2)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write(b"\n")
            self._wait_ready()

    def _wait_ready(self, timeout=5):
        # Arduino sends READY after boot
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode(errors="ignore").strip()
                if line == "READY":
                    self._log("Arduino is ready")
                    return
            time.sleep(0.01)
        self._log("Warning: Arduino READY not received")

    def _send_cmd(self, cmd_str):
        # Blocking wait for DONE/ERROR to match firmware protocol
        self._open_serial()
        self._log(f"[Python] {cmd_str}")
        self.ser.write((cmd_str + "\n").encode())

        start_time = time.time()
        while True:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode(errors="ignore").strip()
                self._log(f"[Arduino] {line}")
                if line == "DONE":
                    break
                if line.startswith("ERROR"):
                    break
            if time.time() - start_time > 30:
                self._log("Warning: command timeout")
                break
            time.sleep(0.01)

    def _axis_name(self, axis):
        # Axis mapping matches motors.py: A->STIR, B->SWITCH
        if axis in ("A", "a", 0, "0"):
            return "STIR"
        if axis in ("B", "b", 1, "1"):
            return "SWITCH"
        raise ValueError("axis must be 'A' or 'B'")

    def _record(self, axis, cmd):
        self.commands_log.append(f"{axis}:{cmd}")

    def set_speed_us(self, axis, pulse_delay_us):
        name = self._axis_name(axis)
        self._send_cmd(f"{name} S{pulse_delay_us}")
        self._record(name, f"S{pulse_delay_us}")

    def set_speed_rps(self, axis, rps):
        # Firmware uses pulse delay (us). Convert from rps here.
        pulse_delay_us = int(1_000_000 / (rps * STEPS_PER_REVOLUTION * 2))
        self._log(f"{self._axis_name(axis)} rps {rps} -> {pulse_delay_us} us")
        self.set_speed_us(axis, pulse_delay_us)

    def rotate_steps(self, axis, steps):
        name = self._axis_name(axis)
        self._send_cmd(f"{name} G{steps}")
        self._record(name, f"G{steps}")

    def rotate_revolutions(self, axis, revs):
        steps = int(revs * STEPS_PER_REVOLUTION)
        self._log(f">>> {self._axis_name(axis)} rotate {revs} revs ({steps} steps)")
        self.rotate_steps(axis, steps)

    def set_speed_us_both(self, pulse_delay_us):
        self._send_cmd(f"BOTH S{pulse_delay_us}")
        self._record("BOTH", f"S{pulse_delay_us}")

    def set_speed_rps_both(self, rps):
        # BOTH applies to both motors on the Mega
        pulse_delay_us = int(1_000_000 / (rps * STEPS_PER_REVOLUTION * 2))
        self._log(f"BOTH rps {rps} -> {pulse_delay_us} us")
        self.set_speed_us_both(pulse_delay_us)

    def rotate_steps_both(self, steps):
        self._send_cmd(f"BOTH G{steps}")
        self._record("BOTH", f"G{steps}")

    def rotate_revolutions_both(self, revs):
        steps = int(revs * STEPS_PER_REVOLUTION)
        self._log(f">>> BOTH rotate {revs} revs ({steps} steps)")
        self.rotate_steps_both(steps)

    def get_commands_log(self):
        return self.commands_log.copy()

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        self._log("Stepper port closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    controller = ExtractionStepperController(port="COM9")
    try:
        controller.set_speed_rps("B", 1.5)
        time.sleep(0.2)
        # controller.rotate_revolutions("A", 0.25)
        time.sleep(0.2)
        controller.rotate_revolutions("B", 0.25)
    finally:
        controller.close()
