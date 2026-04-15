"""Test for Feishu approval card PATCH API fix.

Issue: #10154 - Approval card update fails with error 200340 because
SDK uses PUT API internally. Fixed by using PATCH API directly.
"""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestPatchApprovalCard:
    """Test that approval cards use PATCH API instead of PUT."""

    def test_patch_message_classes_imported(self):
        """PatchMessage classes should be imported when SDK available."""
        from gateway.platforms.feishu import FEISHU_AVAILABLE
        if FEISHU_AVAILABLE:
            from gateway.platforms.feishu import PatchMessageRequest, PatchMessageRequestBody
            assert PatchMessageRequest is not None
            assert PatchMessageRequestBody is not None

    def test_build_patch_message_body(self):
        """_build_patch_message_body should build correct request body."""
        from gateway.platforms.feishu import FeishuAdapter
        
        content = '{"config": {"wide_screen_mode": true}}'
        body = FeishuAdapter._build_patch_message_body(content=content)
        
        # Body should have content attribute
        assert hasattr(body, 'content')
        assert body.content == content

    def test_build_patch_message_request(self):
        """_build_patch_message_request should build correct request."""
        from gateway.platforms.feishu import FeishuAdapter
        
        message_id = "test_message_123"
        body = MagicMock()
        request = FeishuAdapter._build_patch_message_request(message_id=message_id, request_body=body)
        
        # Request should have message_id and request_body
        assert hasattr(request, 'message_id')
        assert request.message_id == message_id

    @pytest.mark.asyncio
    async def test_patch_approval_card_calls_patch_api(self):
        """_patch_approval_card should call PATCH API, not PUT API."""
        from gateway.platforms.feishu import FeishuAdapter
        
        # Mock adapter with client
        adapter = MagicMock(spec=FeishuAdapter)
        adapter._client = MagicMock()
        adapter._build_patch_message_body = FeishuAdapter._build_patch_message_body
        adapter._build_patch_message_request = FeishuAdapter._build_patch_message_request
        
        # Mock PATCH API response
        mock_response = MagicMock()
        mock_response.success.return_value = True
        adapter._client.im.v1.message.patch = MagicMock(return_value=mock_response)
        
        message_id = "test_msg"
        card_json = json.dumps({"config": {"wide_screen_mode": True}})
        
        # Call the method
        await FeishuAdapter._patch_approval_card(adapter, message_id, card_json)
        
        # Verify PATCH API was called
        assert adapter._client.im.v1.message.patch.called
        # Verify PUT API was NOT called
        assert not adapter._client.im.v1.message.update.called

    @pytest.mark.asyncio
    async def test_patch_approval_card_handles_failure(self):
        """_patch_approval_card should log warning on failure."""
        from gateway.platforms.feishu import FeishuAdapter
        
        adapter = MagicMock(spec=FeishuAdapter)
        adapter._client = MagicMock()
        adapter._build_patch_message_body = FeishuAdapter._build_patch_message_body
        adapter._build_patch_message_request = FeishuAdapter._build_patch_message_request
        
        # Mock failed response
        mock_response = MagicMock()
        mock_response.success.return_value = False
        adapter._client.im.v1.message.patch = MagicMock(return_value=mock_response)
        
        message_id = "test_msg"
        card_json = json.dumps({"config": {"wide_screen_mode": True}})
        
        # Should not raise, just log
        await FeishuAdapter._patch_approval_card(adapter, message_id, card_json)

    def test_build_resolved_approval_card(self):
        """_build_resolved_approval_card should build correct card JSON."""
        from gateway.platforms.feishu import FeishuAdapter
        
        card = FeishuAdapter._build_resolved_approval_card(choice="approve", user_name="TestUser")
        
        # Card should have correct structure
        assert "config" in card
        assert "header" in card
        assert "elements" in card
        
        # Header should show approval
        assert "✅" in card["header"]["title"]["content"]
        assert "Approved" in card["header"]["title"]["content"]

    def test_build_resolved_approval_card_deny(self):
        """_build_resolved_approval_card for deny should show deny."""
        from gateway.platforms.feishu import FeishuAdapter
        
        card = FeishuAdapter._build_resolved_approval_card(choice="deny", user_name="TestUser")
        
        # Header should show deny
        assert "❌" in card["header"]["title"]["content"]
        assert "Denied" in card["header"]["title"]["content"]


class TestApprovalCardActionHandling:
    """Test approval card action handling."""

    def test_handle_approval_card_action_gets_message_id(self):
        """_handle_approval_card_action should extract message_id from event."""
        from gateway.platforms.feishu import FeishuAdapter
        
        # Mock event with message_id
        event = MagicMock()
        message = MagicMock()
        message.message_id = "msg_123"
        event.message = message
        event.operator = MagicMock()
        event.operator.open_id = "user_123"
        
        action_value = {"approval_id": "approval_123", "hermes_action": "approve"}
        loop = MagicMock()
        
        # Mock methods
        adapter = MagicMock(spec=FeishuAdapter)
        adapter._get_cached_sender_name = MagicMock(return_value="TestUser")
        adapter._submit_on_loop = MagicMock()
        adapter._build_resolved_approval_card = FeishuAdapter._build_resolved_approval_card
        
        # Call method
        result = FeishuAdapter._handle_approval_card_action(
            adapter, event=event, action_value=action_value, loop=loop
        )
        
        # Should submit PATCH task
        assert adapter._submit_on_loop.called

    def test_patch_vs_put_api_usage(self):
        """PATCH should be used for cards, PUT for text messages."""
        from gateway.platforms.feishu import FeishuAdapter
        
        # _build_patch_message_body for interactive cards
        patch_body = FeishuAdapter._build_patch_message_body(content='{"card": true}')
        assert hasattr(patch_body, 'content')
        # No msg_type for PATCH
        
        # _build_update_message_body for text messages
        update_body = FeishuAdapter._build_update_message_body(
            content="text", msg_type="text", receive_id_type="open_id"
        )
        assert hasattr(update_body, 'content')
        assert hasattr(update_body, 'msg_type')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])