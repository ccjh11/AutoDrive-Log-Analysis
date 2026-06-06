import pytest
from core.rule_engine import RuleEngine

# 1. 制造一个“假”的帧对象 (Mock Object)，用来骗过你的 getattr
class DummyFrame:
    def __init__(self, msg_id, time):
        self.msg_id = msg_id
        self.time = time

def test_check_network_timeout():
    # 2. 准备假数据 (Arrange)：模拟 ID 为 100 的 CAN 报文
    # 第一帧 0ms，第二帧 50ms，第三帧直接跳到了 200ms (产生了 150ms 的断层掉线！)
    mock_frames = [
        DummyFrame(msg_id=100, time=0.0),
        DummyFrame(msg_id=100, time=50.0),
        DummyFrame(msg_id=100, time=200.0) 
    ]
    
    # 3. 实例化你的规则引擎类
    engine = RuleEngine(mock_frames)
    
    # 4. 执行断线检测 (Act)
    # 注意：根据你第 28 行的代码，必须传入 target_id，否则直接 return
    engine.check_network_timeout(target_id=100, max_gap_ms=100)
    
    # 5. 断言结果 (Assert)
    # 只要你的 engine 把抓到的 Bug 存进了 self.reports，这个列表长度就应该大于 0
    assert len(engine.reports) > 0