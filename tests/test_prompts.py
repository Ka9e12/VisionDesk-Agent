import unittest

from desktop_agent.planner.prompts import SYSTEM_PROMPT


class PromptTests(unittest.TestCase):
    def test_wechat_message_workflow_requires_result_selection_and_verification(self):
        self.assertIn("微信/企业微信发送消息必须遵守", SYSTEM_PROMPT)
        self.assertIn("不要直接按 Enter 打开第一个结果", SYSTEM_PROMPT)
        self.assertIn("点击与用户指定联系人或群聊名称匹配的结果", SYSTEM_PROMPT)
        self.assertIn("确认当前对话框就是用户指定的联系人或群聊", SYSTEM_PROMPT)
        self.assertIn("每个新任务都必须在本轮任务中重新搜索并选择目标", SYSTEM_PROMPT)
        self.assertIn("看起来像", SYSTEM_PROMPT)
        self.assertIn("确认当前会话仍是正确联系人或群聊", SYSTEM_PROMPT)
        self.assertIn("发送前的 thought 或发送动作 reason", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
