"""
Review Persistence Skill 单元测试
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch
from datetime import datetime

# 添加 scripts 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from review_persistence import ReviewStateManager
from redis_client import RedisClient


class TestRedisClient:
    """Redis 客户端测试"""
    
    def test_singleton(self):
        """测试单例模式"""
        client1 = RedisClient()
        client2 = RedisClient()
        assert client1 is client2
    
    @patch('redis.Redis')
    def test_connect_success(self, mock_redis):
        """测试连接成功"""
        mock_instance = Mock()
        mock_instance.ping.return_value = True
        mock_redis.return_value = mock_instance
        
        client = RedisClient()
        assert client.is_connected
    
    @patch('redis.Redis')
    def test_connect_failure(self, mock_redis):
        """测试连接失败"""
        import redis
        mock_redis.side_effect = redis.ConnectionError("Connection refused")
        
        client = RedisClient()
        assert not client.is_connected


class TestReviewStateManager:
    """状态管理器测试"""
    
    @pytest.fixture
    def manager(self):
        """创建测试管理器"""
        return ReviewStateManager(
            task_id="test_task_123",
            org_id="test_org_456",
            user_id="test_user_789"
        )
    
    @patch('review_persistence.redis_client')
    def test_save_state(self, mock_redis_client, manager):
        """测试保存状态"""
        mock_redis = Mock()
        mock_redis_client.client = mock_redis
        
        context = {'task_name': '测试项目', 'current_round': 1}
        history = [{'round': 1, 'changes': '初始版本'}]
        
        success = manager.save_state(
            state='REVIEW_IN_PROGRESS',
            context=context,
            modification_history=history
        )
        
        assert success
        mock_redis.setex.assert_called_once()
    
    @patch('review_persistence.redis_client')
    def test_load_state(self, mock_redis_client, manager):
        """测试加载状态"""
        mock_redis = Mock()
        mock_redis_client.client = mock_redis
        
        expected_data = {
            'state': 'REVIEW_IN_PROGRESS',
            'task_name': '测试项目',
            'modification_count': 1
        }
        mock_redis.get.return_value = expected_data
        
        result = manager.load_state()
        
        assert result == expected_data
        mock_redis.get.assert_called_once()
    
    @patch('review_persistence.redis_client')
    def test_delete_state(self, mock_redis_client, manager):
        """测试删除状态"""
        mock_redis = Mock()
        mock_redis_client.client = mock_redis
        
        success = manager.delete_state()
        
        assert success
        mock_redis.delete.assert_called_once()
    
    @patch('review_persistence.redis_client')
    def test_get_user_pending_tasks(self, mock_redis_client, manager):
        """测试获取用户未完成任务"""
        mock_redis = Mock()
        mock_redis_client.client = mock_redis
        
        task_ids = {'task_1', 'task_2'}
        mock_redis.smembers.return_value = task_ids
        mock_redis.get.side_effect = [
            {'task_id': 'task_1', 'task_name': '项目 1'},
            {'task_id': 'task_2', 'task_name': '项目 2'}
        ]
        
        result = manager.get_user_pending_tasks()
        
        assert len(result) == 2
    
    def test_format_pending_message(self, manager):
        """测试格式化未完成消息"""
        pending_tasks = [
            {
                'task_name': 'XX 项目',
                'state': 'REVIEW_IN_PROGRESS',
                'last_modified': datetime.now().isoformat(),
                'modification_count': 3
            }
        ]
        
        message = manager.format_pending_message(pending_tasks)
        
        assert 'XX 项目' in message
        assert '审核中' in message
        assert '3 轮' in message


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
