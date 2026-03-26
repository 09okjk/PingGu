"""
Review Persistence Skill - 主入口
提供状态持久化与恢复的命令行接口
"""

# Windows 编码修复
import sys
import io
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )

import argparse
import json
import logging
from typing import Optional

from .review_persistence import ReviewStateManager
from .redis_client import redis_client
from .state_machine_integration import StateMachineIntegration
from .agent_bootstrap import AgentBootstrap
from .notification_handler import NotificationHandler
from .redis_lock import RedisLock
from .deployment_config import DeploymentConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_save(args):
    """保存状态命令"""
    manager = ReviewStateManager(
        task_id=args.task_id,
        org_id=args.org_id,
        user_id=args.user_id
    )
    
    context = json.loads(args.context) if args.context else {}
    history = json.loads(args.history) if args.history else []
    
    success = manager.save_state(
        state=args.state,
        context=context,
        modification_history=history
    )
    
    if success:
        print(f"✅ 状态已保存：{args.task_id}")
        return 0
    else:
        print(f"❌ 状态保存失败：{args.task_id}")
        return 1


def cmd_load(args):
    """加载状态命令"""
    manager = ReviewStateManager(task_id=args.task_id)
    state_data = manager.load_state()
    
    if state_data:
        print(json.dumps(state_data, ensure_ascii=False, indent=2))
        return 0
    else:
        print(f"未找到状态：{args.task_id}")
        return 1


def cmd_delete(args):
    """删除状态命令"""
    manager = ReviewStateManager(task_id=args.task_id)
    success = manager.delete_state()
    
    if success:
        print(f"✅ 状态已删除：{args.task_id}")
        return 0
    else:
        print(f"❌ 状态删除失败：{args.task_id}")
        return 1


def cmd_list_user(args):
    """列出用户未完成任务"""
    manager = ReviewStateManager(user_id=args.user_id)
    pending_tasks = manager.get_user_pending_tasks()
    
    if pending_tasks:
        print(manager.format_pending_message(pending_tasks))
        return 0
    else:
        print("✅ 没有未完成的评估单")
        return 0


def cmd_list_global(args):
    """列出全局未完成任务"""
    manager = ReviewStateManager()
    pending_tasks = manager.get_global_pending_tasks(limit=args.limit)
    
    if pending_tasks:
        print(manager.format_pending_message(pending_tasks))
        return 0
    else:
        print("✅ 没有未完成的评估单")
        return 0


def cmd_find(args):
    """根据名称查找任务"""
    manager = ReviewStateManager(user_id=args.user_id if hasattr(args, 'user_id') else None)
    task = manager.get_task_by_name(args.name)
    
    if task:
        print(json.dumps(task, ensure_ascii=False, indent=2))
        return 0
    else:
        print(f"未找到任务：{args.name}")
        return 1


def cmd_status(args):
    """检查 Redis 连接状态"""
    if redis_client.is_connected:
        print("✅ Redis 连接正常")
        return 0
    else:
        print("❌ Redis 未连接")
        return 1


def cmd_recover(args):
    """Phase 4: 状态恢复命令"""
    bootstrap = AgentBootstrap()
    
    if args.task_id:
        # 恢复指定任务
        recovered = bootstrap.recover_single_state(args.task_id)
        if recovered:
            print(f"✅ 状态已恢复：{args.task_id}")
            print(json.dumps(recovered, ensure_ascii=False, indent=2))
            return 0
        else:
            print(f"❌ 无法恢复状态：{args.task_id}")
            return 1
    else:
        # 恢复所有未完成状态
        recovered_count = bootstrap.recover_all_states()
        print(f"✅ 已恢复 {recovered_count} 个未完成状态")
        return 0


def cmd_notify(args):
    """Phase 5: 用户通知命令"""
    notifier = NotificationHandler()
    
    if args.user_id:
        # 通知指定用户
        pending_tasks = notifier.get_user_pending_tasks(args.user_id)
        if pending_tasks:
            message = notifier.format_welcome_back_message(pending_tasks)
            print(message)
            return 0
        else:
            print(f"✅ 用户 {args.user_id} 没有未完成任务")
            return 0
    else:
        # 批量通知所有有未完成任务的用户
        notified_count = notifier.notify_all_users_with_pending_tasks()
        print(f"✅ 已通知 {notified_count} 个用户")
        return 0


def cmd_lock(args):
    """优化：获取分布式锁"""
    lock = RedisLock(f"lock:{args.resource}")
    
    if args.release:
        # 释放锁
        success = lock.release()
        if success:
            print(f"✅ 锁已释放：{args.resource}")
            return 0
        else:
            print(f"❌ 锁释放失败：{args.resource}")
            return 1
    else:
        # 获取锁
        acquired = lock.acquire(timeout=args.timeout)
        if acquired:
            print(f"✅ 锁已获取：{args.resource}")
            return 0
        else:
            print(f"❌ 无法获取锁：{args.resource} (超时 {args.timeout}s)")
            return 1


def cmd_deploy_config(args):
    """部署：检查部署配置"""
    config = DeploymentConfig()
    
    if args.check:
        # 检查配置
        issues = config.validate_config()
        if issues:
            print("❌ 配置问题:")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        else:
            print("✅ 配置检查通过")
            return 0
    elif args.show:
        # 显示当前配置
        current_config = config.get_current_config()
        print(json.dumps(current_config, ensure_ascii=False, indent=2))
        return 0
    elif args.test_connection:
        # 测试 Redis 连接
        success = config.test_redis_connection()
        if success:
            print("✅ Redis 连接测试通过")
            return 0
        else:
            print("❌ Redis 连接测试失败")
            return 1
    else:
        # 显示部署指南
        print(config.get_deployment_guide())
        return 0


def cmd_integrate(args):
    """Phase 3: 状态机集成命令"""
    integration = StateMachineIntegration()
    
    if args.task_id:
        # 集成指定任务的状态机
        success = integration.sync_state_machine_state(args.task_id)
        if success:
            print(f"✅ 状态机已同步：{args.task_id}")
            return 0
        else:
            print(f"❌ 状态机同步失败：{args.task_id}")
            return 1
    else:
        print("请指定 --task-id 参数")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Review Persistence Skill - 评估单状态持久化',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # save 命令
    save_parser = subparsers.add_parser('save', help='保存状态')
    save_parser.add_argument('--task-id', required=True, help='评估单 ID')
    save_parser.add_argument('--org-id', required=True, help='组织 ID')
    save_parser.add_argument('--user-id', required=True, help='用户 ID')
    save_parser.add_argument('--state', required=True, help='状态值')
    save_parser.add_argument('--context', default='{}', help='上下文 JSON')
    save_parser.add_argument('--history', default='[]', help='修改历史 JSON')
    save_parser.set_defaults(func=cmd_save)
    
    # load 命令
    load_parser = subparsers.add_parser('load', help='加载状态')
    load_parser.add_argument('--task-id', required=True, help='评估单 ID')
    load_parser.set_defaults(func=cmd_load)
    
    # delete 命令
    delete_parser = subparsers.add_parser('delete', help='删除状态')
    delete_parser.add_argument('--task-id', required=True, help='评估单 ID')
    delete_parser.set_defaults(func=cmd_delete)
    
    # list-user 命令
    list_user_parser = subparsers.add_parser('list-user', help='列出用户未完成任务')
    list_user_parser.add_argument('--user-id', required=True, help='用户 ID')
    list_user_parser.set_defaults(func=cmd_list_user)
    
    # list-global 命令
    list_global_parser = subparsers.add_parser('list-global', help='列出全局未完成任务')
    list_global_parser.add_argument('--limit', type=int, default=50, help='返回数量限制')
    list_global_parser.set_defaults(func=cmd_list_global)
    
    # find 命令
    find_parser = subparsers.add_parser('find', help='根据名称查找任务')
    find_parser.add_argument('--name', required=True, help='任务名称')
    find_parser.add_argument('--user-id', help='用户 ID (可选)')
    find_parser.set_defaults(func=cmd_find)
    
    # status 命令
    status_parser = subparsers.add_parser('status', help='检查 Redis 连接状态')
    status_parser.set_defaults(func=cmd_status)
    
    # recover 命令 (Phase 4)
    recover_parser = subparsers.add_parser('recover', help='恢复状态 (Phase 4)')
    recover_parser.add_argument('--task-id', help='评估单 ID (可选，不指定则恢复所有)')
    recover_parser.set_defaults(func=cmd_recover)
    
    # notify 命令 (Phase 5)
    notify_parser = subparsers.add_parser('notify', help='用户通知 (Phase 5)')
    notify_parser.add_argument('--user-id', help='用户 ID (可选，不指定则通知所有用户)')
    notify_parser.set_defaults(func=cmd_notify)
    
    # lock 命令 (优化)
    lock_parser = subparsers.add_parser('lock', help='分布式锁管理 (优化)')
    lock_parser.add_argument('--resource', required=True, help='资源名称')
    lock_parser.add_argument('--timeout', type=int, default=10, help='超时时间 (秒)')
    lock_parser.add_argument('--release', action='store_true', help='释放锁')
    lock_parser.set_defaults(func=cmd_lock)
    
    # deploy-config 命令 (部署)
    deploy_config_parser = subparsers.add_parser('deploy-config', help='部署配置 (部署)')
    deploy_config_parser.add_argument('--check', action='store_true', help='检查配置')
    deploy_config_parser.add_argument('--show', action='store_true', help='显示当前配置')
    deploy_config_parser.add_argument('--test-connection', action='store_true', help='测试 Redis 连接')
    deploy_config_parser.set_defaults(func=cmd_deploy_config)
    
    # integrate 命令 (Phase 3)
    integrate_parser = subparsers.add_parser('integrate', help='状态机集成 (Phase 3)')
    integrate_parser.add_argument('--task-id', required=True, help='评估单 ID')
    integrate_parser.set_defaults(func=cmd_integrate)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
