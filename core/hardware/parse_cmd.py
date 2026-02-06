import re
def parse_cmd(cmd):
    """解析CMD命令的含义"""
    cmd = cmd.strip()
    if not cmd.startswith('/'):
        return "未知命令"
    
    parts = cmd[1:].rstrip('R\r\n')

    pump = parts[0]
    action = parts[1:]
    # 解析动作
    if action == 'Z':
        return f"泵{pump}归零复位 (初始化)"
    elif action[0] in ('I', 'O'):
        direction = "吸液" if action[0] == 'I' else "排液"
        port = action[1:]
        return f"泵{pump}切换到端口{port} ({direction}方向)"
    elif action[0] == 'V':
        match = re.match(r'V(\d+)([AD])(\d+)', action)
        if match:
            speed = match.group(1)
            op = match.group(2)
            count = int(match.group(3))
            volume = count / 240.0
            
            if op == 'A':
                if count == 0:
                    return f"泵{pump}以速度{speed}全部排出(归零)"
                else:
                    return f"泵{pump}以速度{speed}吸取 {volume:.2f}mL ({count}计数)"
            elif op == 'D':
                return f"泵{pump}以速度{speed}排出 {volume:.2f}mL ({count}计数)"
    
    return f"泵{pump}执行: {action}"
