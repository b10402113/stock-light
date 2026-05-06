from enum import IntEnum


class ErrorCode(IntEnum):
    """錯誤碼枚舉"""

    # 成功
    SUCCESS = 0

    # 通用錯誤 (1-99)
    UNKNOWN_ERROR = 1
    PARAM_ERROR = 2
    RESOURCE_NOT_FOUND = 3
    RESOURCE_ALREADY_EXISTS = 4
    OPERATION_FAILED = 5

    # 認證/授權錯誤 (100-199)
    UNAUTHORIZED = 100
    TOKEN_EXPIRED = 101
    TOKEN_INVALID = 102
    PERMISSION_DENIED = 103

    # 用戶模塊錯誤 (200-299)
    USER_NOT_FOUND = 200
    USER_ALREADY_EXISTS = 201
    USER_DISABLED = 202
    LINE_USER_NOT_FOUND = 203

    # 股票模塊錯誤 (300-399)
    STOCK_NOT_FOUND = 300
    STOCK_PRICE_NOT_FOUND = 301
    INDICATOR_CALCULATION_FAILED = 302

    # 訂閱模塊錯誤 (400-499)
    SUBSCRIPTION_NOT_FOUND = 400
    SUBSCRIPTION_ALREADY_EXISTS = 401
    SUBSCRIPTION_LIMIT_EXCEEDED = 402
    ALERT_CONDITION_INVALID = 403

    # 外部服務錯誤 (500-599)
    FUGO_API_ERROR = 500
    FUGLE_API_ERROR = 500  # Alias for Fugle API (same as FUGO)
    LINE_API_ERROR = 501
    EXTERNAL_SERVICE_TIMEOUT = 502
    YFINANCE_API_ERROR = 503
    REDIS_CONNECTION_ERROR = 504
    REDIS_OPERATION_ERROR = 505

    # 系統錯誤 (900-999)
    DATABASE_ERROR = 900
    INTERNAL_ERROR = 999

    @property
    def message(self) -> str:
        """取得錯誤碼對應的預設訊息"""
        messages = {
            ErrorCode.SUCCESS: "成功",
            ErrorCode.UNKNOWN_ERROR: "未知錯誤",
            ErrorCode.PARAM_ERROR: "參數錯誤",
            ErrorCode.RESOURCE_NOT_FOUND: "資源不存在",
            ErrorCode.RESOURCE_ALREADY_EXISTS: "資源已存在",
            ErrorCode.OPERATION_FAILED: "操作失敗",
            ErrorCode.UNAUTHORIZED: "未授權",
            ErrorCode.TOKEN_EXPIRED: "Token 已過期",
            ErrorCode.TOKEN_INVALID: "Token 無效",
            ErrorCode.PERMISSION_DENIED: "權限不足",
            ErrorCode.USER_NOT_FOUND: "用戶不存在",
            ErrorCode.USER_ALREADY_EXISTS: "用戶已存在",
            ErrorCode.USER_DISABLED: "用戶已停用",
            ErrorCode.LINE_USER_NOT_FOUND: "LINE 用戶不存在",
            ErrorCode.STOCK_NOT_FOUND: "股票不存在",
            ErrorCode.STOCK_PRICE_NOT_FOUND: "股票價格不存在",
            ErrorCode.INDICATOR_CALCULATION_FAILED: "指標計算失敗",
            ErrorCode.SUBSCRIPTION_NOT_FOUND: "訂閱不存在",
            ErrorCode.SUBSCRIPTION_ALREADY_EXISTS: "訂閱已存在",
            ErrorCode.SUBSCRIPTION_LIMIT_EXCEEDED: "訂閱數量超過上限",
            ErrorCode.ALERT_CONDITION_INVALID: "警報條件無效",
            ErrorCode.FUGO_API_ERROR: "Fugo API 錯誤",
            ErrorCode.FUGLE_API_ERROR: "Fugle API 錯誤",
            ErrorCode.LINE_API_ERROR: "LINE API 錯誤",
            ErrorCode.EXTERNAL_SERVICE_TIMEOUT: "外部服務超時",
            ErrorCode.YFINANCE_API_ERROR: "YFinance API 錯誤",
            ErrorCode.REDIS_CONNECTION_ERROR: "Redis 連線錯誤",
            ErrorCode.REDIS_OPERATION_ERROR: "Redis 操作錯誤",
            ErrorCode.DATABASE_ERROR: "資料庫錯誤",
            ErrorCode.INTERNAL_ERROR: "系統內部錯誤",
        }
        return messages.get(self, "未知錯誤")


class BizException(Exception):
    """業務異常類"""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str | None = None,
    ):
        self.error_code = error_code
        self.message = message or error_code.message
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"BizException(code={self.error_code}, message={self.message})"
