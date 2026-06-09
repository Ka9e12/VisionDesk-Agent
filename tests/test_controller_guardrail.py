import tempfile
import unittest
from pathlib import Path

from desktop_agent.config import AgentConfig
from desktop_agent.controller import AgentController
from desktop_agent.memory.task_memory import TaskMemory
from desktop_agent.schema import Action, ActionResult


def _controller() -> AgentController:
    tmp = tempfile.TemporaryDirectory()
    controller = AgentController(
        AgentConfig(
            api_key="key",
            api_base="http://example.test",
            model="model",
            log_dir=Path(tmp.name),
        )
    )
    controller._test_tmp = tmp
    return controller


class WeChatGuardrailTests(unittest.TestCase):
    def test_blocks_enter_send_without_selected_target_result(self):
        controller = _controller()
        controller.memory = TaskMemory("在微信给尹文凯发送，你好")

        message = controller._wechat_send_guard_message(
            "在微信给尹文凯发送，你好",
            [Action(type="press", params={"key": "enter"}, risk="high")],
        )

        self.assertIsNotNone(message)
        self.assertIn("尹文凯", message)

    def test_allows_enter_send_after_matching_search_result_click(self):
        controller = _controller()
        controller.memory = TaskMemory("在微信给尹文凯发送，你好")
        controller.memory.add_result(
            ActionResult(
                action=Action(
                    type="click",
                    params={"x": 10, "y": 20},
                    reason="点击搜索结果中匹配的联系人“尹文凯”",
                ),
                success=True,
                message="ok",
            )
        )

        message = controller._wechat_send_guard_message(
            "在微信给尹文凯发送，你好",
            [Action(type="press", params={"key": "enter"}, risk="high")],
            "会话标题显示为尹文凯，严格确认当前会话对象正确，准备发送。",
        )

        self.assertIsNone(message)

    def test_blocks_enter_send_without_strict_confirmation(self):
        controller = _controller()
        controller.memory = TaskMemory("在微信给尹文凯发送，你好")
        controller.memory.add_result(
            ActionResult(
                action=Action(
                    type="click",
                    params={"x": 10, "y": 20},
                    reason="点击搜索结果中匹配的联系人“尹文凯”",
                ),
                success=True,
                message="ok",
            )
        )

        message = controller._wechat_send_guard_message(
            "在微信给尹文凯发送，你好",
            [Action(type="press", params={"key": "enter"}, risk="high")],
            "当前标题位置看起来像尹文凯，准备发送。",
        )

        self.assertIsNotNone(message)
        self.assertIn("严格确认", message)

    def test_extracts_common_wechat_targets(self):
        controller = _controller()

        examples = {
            "任务: 微信发消息给胡鹏飞说1il。": "胡鹏飞",
            "在微信给尹文凯发送，你是河豚吗？怎么这么膨胀": "尹文凯",
            "在微信发送消息给文件传输助手：hello": "文件传输助手",
            "在微信群聊“产品测试群”发送 hello": "产品测试群",
            "微信给群聊项目群发消息：收到": "项目群",
        }

        for task, target in examples.items():
            with self.subTest(task=task):
                self.assertEqual(controller._wechat_target_from_task(task), target)


if __name__ == "__main__":
    unittest.main()
