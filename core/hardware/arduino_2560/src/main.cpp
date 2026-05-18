#include <Arduino.h>
#include <AccelStepper.h>

// 定义连接到驱动器负极(-)的引脚
// 共阳极接法: PUL+, DIR+, ENA+ 接 5V
// PUL- 接 D2, DIR- 接 D3, ENA- 接 D4
const int PIN_STEP = 2;   // 连接 PUL-
const int PIN_DIR = 3;    // 连接 DIR-
const int PIN_ENABLE = 4; // 连接 ENA-

// 定义电机参数
// 降低速度和加速度以防止堵转
const int DEFAULT_SPEED = 600;  
const int DEFAULT_ACCEL = 500; // 原来2000太快了，容易导致启动瞬间堵转

// 创建步进电机对象
// 1 = AccelStepper::DRIVER (意味着使用驱动器, 2个引脚控制)
AccelStepper stepper(AccelStepper::DRIVER, PIN_STEP, PIN_DIR);

// 状态变量
String inputString = "";
boolean stringComplete = false;
boolean isRunning = false; // 标记电机是否正在执行运动任务

// 函数声明
void parseCommand(String cmd);

void setup() {
  Serial.begin(9600);
  
  // 【关键步骤】适配共阳极接法！
  // 参数顺序: directionInvert, stepInvert, enableInvert
  // 这里全设为 true，告诉库：引脚输出 LOW 代表"激活/动作"，平时保持 HIGH
  stepper.setPinsInverted(true, true, true);
  
  // 【重要调整】暂时注释掉Enable引脚设置
  // 很多驱动器默认悬空即为Enable。如果逻辑搞反会导致电机无力。
  // 建议物理上拔掉驱动器ENA+, ENA-的线，确保电机始终锁止。
  // stepper.setEnablePin(PIN_ENABLE); 
  // stepper.enableOutputs(); 

  stepper.setMaxSpeed(3000); // 降低最大速度上限
  stepper.setAcceleration(DEFAULT_ACCEL);
  stepper.setSpeed(DEFAULT_SPEED);
  
  Serial.println("Ready"); // 简化启动信息方便上位机解析
}

void loop() {
  // 必须不断调用 run()
  stepper.run();

  // 检查是否刚刚完成运动
  if (isRunning && stepper.distanceToGo() == 0) {
    isRunning = false;
    Serial.println("Done"); // 发送完成信号
  }

  // 如果此时又有新命令（比如在运动中途发了新位置），isRunning会被重新置位true

  if (stringComplete) {
    parseCommand(inputString);
    inputString = "";
    stringComplete = false;
  }
}

// 串口事件
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}

void parseCommand(String cmd) {
  cmd.trim();
  int separatorIndex = cmd.indexOf(':');
  
  if (separatorIndex == -1) {
    // 格式错误时的反馈
    Serial.println("Error: Invalid Format");
    return;
  }

  char commandChar = cmd.charAt(0);
  long value = cmd.substring(separatorIndex + 1).toInt();

  switch (commandChar) {
    case 'M': // 相对移动
      Serial.print("Move: "); Serial.println(value);
      stepper.move(value); 
      isRunning = true; // 标记开始运动
      break;
    case 'A': // 绝对移动
      Serial.print("Abs Move: "); Serial.println(value);
      stepper.moveTo(value);
      isRunning = true; // 标记开始运动
      break;
    case 'S': // 设速度
      stepper.setMaxSpeed(value);
      Serial.print("Speed: "); Serial.println(value);
      break;
    case 'Z': // 设当前点为零点
      stepper.setCurrentPosition(0);
      Serial.println("Zero Set");
      break; 
    default:
      Serial.print("Error: Unknown Command "); 
      Serial.println(commandChar);
      break;
  }
}