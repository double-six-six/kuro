#!/usr/bin/env python3
"""
Kuro Auto Signin - GitHub Actions 版本
基于 mxyooR/Kuro-autosignin 项目改写[citation:5]
"""

import os
import sys
from datetime import datetime
from typing import Dict, List

from kuro_api import (
    GAME_CONFIG, get_user_info, get_game_roles,
    check_sign_status, do_signin, get_sign_rewards
)

def log_message(msg: str, level: str = "INFO"):
    """带时间戳的日志输出"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")

def format_reward_message(reward: Dict) -> str:
    """格式化奖励消息"""
    if not reward:
        return ""
    
    goods_name = reward.get("goodsName", "未知道具")
    goods_num = reward.get("goodsNum", 1)
    return f"获得 {goods_name} x{goods_num}"

def sign_for_game(token: str, game_type: str, role: Dict) -> Dict:
    """为指定游戏角色签到"""
    game_config = GAME_CONFIG[game_type]
    role_id = role.get("roleId")
    user_id = role.get("userId") or role.get("uid")
    role_name = role.get("roleName", "未知角色")
    server_name = role.get("serverName", "未知服务器")
    
    log_message(f"正在为 [{server_name}] {role_name} 签到...")
    
    # 1. 检查签到状态
    status = check_sign_status(token, game_config["game_id"], role_id, user_id)
    if not status.get("success"):
        return {
            "success": False,
            "role": role_name,
            "error": status.get("error", "检查状态失败")
        }
    
    if status.get("signed_today"):
        log_message(f"  {role_name} 今日已签到，本月已签 {status.get('total_days', 0)} 天")
        return {
            "success": True,
            "role": role_name,
            "already_signed": True,
            "total_days": status.get("total_days", 0)
        }
    
    # 2. 执行签到
    result = do_signin(token, game_config["game_id"], role_id, user_id)
    
    if result.get("success"):
        reward_msg = format_reward_message(result.get("reward", {}))
        log_message(f"  ✓ {role_name} 签到成功！{reward_msg}")
        return {
            "success": True,
            "role": role_name,
            "reward": result.get("reward", {}),
            "message": reward_msg
        }
    else:
        log_message(f"  ✗ {role_name} 签到失败: {result.get('error', '未知错误')}", "ERROR")
        return {
            "success": False,
            "role": role_name,
            "error": result.get("error", "签到失败")
        }

def main() -> bool:
    """主函数"""
    log_message("========== Kuro 自动签到开始 ==========")
    
    # 读取配置
    token = os.environ.get("KURO_TOKEN", "")
    game_type = os.environ.get("SIGN_TYPE", "ww").lower()
    
    if not token:
        log_message("错误：未配置 KURO_TOKEN，请在 GitHub Secrets 中设置", "ERROR")
        log_message("获取 Token 方法：登录库街区后从请求头中获取", "ERROR")
        return False
    
    if game_type not in GAME_CONFIG:
        log_message(f"错误：不支持的签到类型 '{game_type}'，请使用 ww(鸣潮) 或 zs(战双)", "ERROR")
        return False
    
    game_name = GAME_CONFIG[game_type]["name"]
    log_message(f"签到类型: {game_name}")
    
    # 1. 验证 Token 并获取用户信息
    user_info = get_user_info(token)
    if not user_info:
        log_message("Token 验证失败，请检查 Token 是否正确", "ERROR")
        return False
    
    user_name = user_info.get("nickname", "未知用户")
    user_id = user_info.get("userId")
    log_message(f"用户: {user_name}")
    
    # 2. 获取游戏角色列表
    roles = get_game_roles(token, GAME_CONFIG[game_type]["game_id"])
    if not roles:
        log_message(f"未找到 {game_name} 角色，请确认账号已绑定游戏角色", "WARNING")
        return False
    
    log_message(f"找到 {len(roles)} 个角色")
    
    # 3. 执行签到
    results = []
    for role in roles:
        result = sign_for_game(token, game_type, role)
        results.append(result)
    
    # 4. 输出汇总
    log_message("\n========== 签到汇总 ==========")
    success_count = sum(1 for r in results if r.get("success"))
    already_count = sum(1 for r in results if r.get("already_signed"))
    fail_count = len(results) - success_count
    
    log_message(f"总计: {len(results)} 个角色")
    log_message(f"成功: {success_count} (其中今日已签到: {already_count})")
    if fail_count > 0:
        log_message(f"失败: {fail_count}")
        for r in results:
            if not r.get("success"):
                log_message(f"  - {r.get('role')}: {r.get('error', '未知错误')}", "ERROR")
    
    log_message(f"========== 签到{'完成' if fail_count == 0 else '部分失败'} ==========")
    
    return fail_count == 0

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
