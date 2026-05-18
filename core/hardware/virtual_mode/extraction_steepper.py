import time

DEFAULT_PORT = "COM9"
STEPS_PER_REVOLUTION = 400  # Keep consistent with real firmware


class ExtractionStepperController:
    """Virtual dual stepper controller (single Mega board, one COM port)."""

    def __init__(self, port=DEFAULT_PORT):
        self.port = port
        self._logger = print
        self.commands_log = []

    def set_logger(self, logger_func):
        self._logger = logger_func

    def _log(self, msg):
        if self._logger:
            self._logger(msg)

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
        self._log(f"[Virtual] {name} S{pulse_delay_us}")
        self._record(name, f"S{pulse_delay_us}")

    def set_speed_rps(self, axis, rps):
        # Convert rps into pulse delay (us) to match Mega protocol
        pulse_delay_us = int(1_000_000 / (rps * STEPS_PER_REVOLUTION * 2))
        self._log(f"[Virtual] {self._axis_name(axis)} rps {rps} -> {pulse_delay_us} us")
        self.set_speed_us(axis, pulse_delay_us)

    def rotate_steps(self, axis, steps):
        name = self._axis_name(axis)
        self._log(f"[Virtual] {name} G{steps}")
        self._record(name, f"G{steps}")
        time.sleep(0.05)

    def rotate_revolutions(self, axis, revs):
        steps = int(revs * STEPS_PER_REVOLUTION)
        self._log(f"[Virtual] {self._axis_name(axis)} rotate {revs} revs ({steps} steps)")
        self.rotate_steps(axis, steps)

    def set_speed_us_both(self, pulse_delay_us):
        self._log(f"[Virtual] BOTH S{pulse_delay_us}")
        self._record("BOTH", f"S{pulse_delay_us}")

    def set_speed_rps_both(self, rps):
        # BOTH applies to both motors in firmware
        pulse_delay_us = int(1_000_000 / (rps * STEPS_PER_REVOLUTION * 2))
        self._log(f"[Virtual] BOTH rps {rps} -> {pulse_delay_us} us")
        self.set_speed_us_both(pulse_delay_us)

    def rotate_steps_both(self, steps):
        self._log(f"[Virtual] BOTH G{steps}")
        self._record("BOTH", f"G{steps}")
        time.sleep(0.05)

    def rotate_revolutions_both(self, revs):
        steps = int(revs * STEPS_PER_REVOLUTION)
        self._log(f"[Virtual] BOTH rotate {revs} revs ({steps} steps)")
        self.rotate_steps_both(steps)

    def get_commands_log(self):
        return self.commands_log.copy()

    def close(self):
        self._log("[Virtual] Stepper port closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    controller = ExtractionStepperController(port="COM9")
    try:
        controller.set_speed_rps_both(1)
        time.sleep(0.05)
        controller.rotate_revolutions("A", 0.25)
        time.sleep(0.05)
        controller.rotate_revolutions("B", 0.25)
    finally:
        controller.close()
