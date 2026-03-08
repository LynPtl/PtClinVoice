# Phase 5.2 QA Testing Report

**测试日期**: 2026-03-09  
**测试环境**: Ubuntu Linux, Node 20, Python 3.12, Faster-Whisper (small)

## 1. 用户注册 API 测试

| # | 测试用例 | 请求 | 预期 | 实际 | 结果 |
|---|---------|------|------|------|------|
| 1 | 正常注册 | `POST /api/auth/register {"username":"drtest","password":"test123"}` | 201 Created | `{"message":"Registration successful."}` | ✅ PASS |
| 2 | 重复用户名 | 同上（第二次） | 409 Conflict | `{"detail":"Username already exists."}` | ✅ PASS |
| 3 | 用户名过短 | `{"username":"ab","password":"test123"}` | 400 Bad Request | `{"detail":"Username must be at least 3 characters."}` | ✅ PASS |
| 4 | 密码过短 | `{"username":"drvalid","password":"123"}` | 400 Bad Request | `{"detail":"Password must be at least 6 characters."}` | ✅ PASS |

## 2. 注册页面 E2E 测试

| # | 测试步骤 | 预期 | 结果 |
|---|---------|------|------|
| 1 | 访问 `/register` | 显示 Create Account 表单（Username / Password / Confirm Password） | ✅ PASS |
| 2 | 填写信息并提交 | 绿色 Alert "Account created! Redirecting..." | ✅ PASS |
| 3 | 自动跳转 `/login` | 2秒后自动到登录页 | ✅ PASS |
| 4 | 登录页底部链接 | 显示 "Don't have an account? Register here" | ✅ PASS |

## 3. Patient Name 临床标识测试

| # | 测试步骤 | 预期 | 结果 |
|---|---------|------|------|
| 1 | Upload File Tab 显示输入框 | "Patient Name (Optional)" 可见 | ✅ PASS |
| 2 | Record Audio Tab 显示输入框 | "Patient Name (Optional)" 可见 | ✅ PASS |
| 3 | Dashboard 表头 | 显示 `Patient | Created | Status | Actions` | ✅ PASS |

## 4. 任务删除测试

| # | 测试步骤 | 预期 | 结果 |
|---|---------|------|------|
| 1 | 每行显示红色垃圾桶按钮 | 垃圾桶图标可见 | ✅ PASS |
| 2 | 点击垃圾桶 → Modal 弹窗 | "Are you sure..." 二次确认 | ✅ PASS |
| 3 | `DELETE /api/tasks/{id}` 权限校验 | 仅 owner 可删除 | ✅ PASS |

## 5. 跨浏览器一致性

| # | 测试步骤 | 预期 | 结果 |
|---|---------|------|------|
| 1 | 同一账号不同浏览器登录 | 看到相同的 Task 列表 | ✅ PASS |

## 总结
Phase 5.2 全部 12 项测试用例通过，注册/登录/标识/删除功能均达到预期。
