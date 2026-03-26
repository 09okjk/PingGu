"""
部署配置管理
提供生产环境 Redis 连接配置和检查工具
"""

import os
import logging
from typing import Dict, Any, Optional

from .redis_client import redis_client

logger = logging.getLogger(__name__)


class DeploymentConfig:
    """部署配置管理器"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.config = self._load_config_from_env()
    
    def _load_config_from_env(self) -> Dict[str, Any]:
        """
        从环境变量加载配置
        
        Returns:
            配置字典
        """
        return {
            'redis_host': os.getenv('REDIS_HOST', 'localhost'),
            'redis_port': int(os.getenv('REDIS_PORT', '6379')),
            'redis_db': int(os.getenv('REDIS_DB', '0')),
            'redis_password': os.getenv('REDIS_PASSWORD', ''),
            'state_ttl_seconds': int(os.getenv('STATE_TTL_SECONDS', '86400')),
            'pending_list_ttl_seconds': int(os.getenv('PENDING_LIST_TTL_SECONDS', '604800')),
        }
    
    def check_config(self) -> Dict[str, Any]:
        """
        检查配置完整性
        
        Returns:
            检查结果字典
        """
        issues = []
        warnings = []
        info = []
        
        # 检查 Redis 配置
        if not self.config['redis_host']:
            issues.append("REDIS_HOST 未设置")
        else:
            info.append(f"REDIS_HOST: {self.config['redis_host']}")
        
        if not self.config['redis_port']:
            issues.append("REDIS_PORT 未设置")
        else:
            info.append(f"REDIS_PORT: {self.config['redis_port']}")
        
        # 检查 TTL 配置
        if self.config['state_ttl_seconds'] < 3600:
            warnings.append(f"STATE_TTL_SECONDS 过小 ({self.config['state_ttl_seconds']}s), 建议至少 3600s")
        else:
            info.append(f"STATE_TTL_SECONDS: {self.config['state_ttl_seconds']}s")
        
        if self.config['pending_list_ttl_seconds'] < 86400:
            warnings.append(f"PENDING_LIST_TTL_SECONDS 过小 ({self.config['pending_list_ttl_seconds']}s), 建议至少 86400s")
        else:
            info.append(f"PENDING_LIST_TTL_SECONDS: {self.config['pending_list_ttl_seconds']}s")
        
        # 检查密码（仅提示，不显示具体值）
        if self.config['redis_password']:
            info.append("REDIS_PASSWORD: 已设置")
        else:
            warnings.append("REDIS_PASSWORD 未设置（生产环境建议设置密码）")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'info': info,
            'config': self.config
        }
    
    def show_config(self) -> Dict[str, Any]:
        """
        显示当前配置
        
        Returns:
            配置字典（密码已脱敏）
        """
        safe_config = self.config.copy()
        if safe_config.get('redis_password'):
            safe_config['redis_password'] = '***已设置***'
        
        return {
            'config': safe_config,
            'source': 'environment_variables'
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试 Redis 连接
        
        Returns:
            测试结果字典
        """
        try:
            # 使用 redis_client 测试连接
            client = redis_client.get_client()
            
            if not client:
                return {
                    'success': False,
                    'error': '无法创建 Redis 客户端'
                }
            
            # 尝试 PING
            response = client.ping()
            
            if response:
                # 获取 Redis 信息
                info = client.info('server')
                
                return {
                    'success': True,
                    'message': 'Redis 连接成功',
                    'redis_version': info.get('redis_version', 'unknown'),
                    'connected_clients': info.get('connected_clients', 'unknown'),
                    'config': {
                        'host': self.config['redis_host'],
                        'port': self.config['redis_port'],
                        'db': self.config['redis_db']
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'Redis PING 无响应'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'config': {
                    'host': self.config['redis_host'],
                    'port': self.config['redis_port'],
                    'db': self.config['redis_db']
                }
            }
    
    def get_deployment_guide(self) -> str:
        """
        获取部署指南
        
        Returns:
            部署指南文本
        """
        guide = """
# Redis 部署配置指南

## 1. 环境变量配置

创建 `.env` 文件或设置系统环境变量：

```bash
# Redis 连接配置
REDIS_HOST=localhost          # Redis 服务器地址
REDIS_PORT=6379               # Redis 端口
REDIS_DB=0                    # Redis 数据库编号
REDIS_PASSWORD=your_password  # Redis 密码（生产环境必填）

# 状态 TTL 配置（秒）
STATE_TTL_SECONDS=86400       # 状态过期时间（默认 24 小时）
PENDING_LIST_TTL_SECONDS=604800  # 待处理列表过期时间（默认 7 天）
```

## 2. 生产环境建议

### Redis 服务器
- 使用 Redis 6.0+ 版本
- 启用持久化（RDB 或 AOF）
- 配置密码认证
- 限制网络访问（防火墙/安全组）

### 性能优化
- 根据并发量调整 maxclients
- 配置合适的内存限制
- 启用慢查询日志

### 监控
- 监控内存使用率
- 监控连接数
- 监控命中率

## 3. Docker 部署（可选）

```bash
docker run -d \\
  --name redis \\
  -p 6379:6379 \\
  -v redis-data:/data \\
  -e REDIS_PASSWORD=your_password \\
  redis:7-alpine
```

## 4. 验证部署

```bash
# 检查配置
uv run python -m scripts.main deploy-config --check

# 测试连接
uv run python -m scripts.main deploy-config --test-connection
```

## 5. 故障排查

### 连接失败
- 检查 Redis 服务是否运行
- 检查防火墙设置
- 验证密码是否正确

### 性能问题
- 检查内存使用
- 检查慢查询日志
- 考虑增加连接池大小
"""
        return guide
