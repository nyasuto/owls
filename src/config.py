"""
設定管理モジュール

設定の優先順位：環境変数 > config.yml > デフォルト値
後方互換性を保ちながら、設定の外部化を実現します。
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigError(Exception):
    """設定関連のエラー"""

    pass


class ConfigLoader:
    """設定ローダークラス

    YAML設定ファイルと環境変数から設定を読み込み、
    デフォルト値とマージして最終的な設定を提供します。
    """

    def __init__(self, config_path: Optional[str] = None):
        """初期化

        Args:
            config_path: 設定ファイルのパス。Noneの場合はconfig.ymlを探索
        """
        self.config_path = self._find_config_file(config_path)
        self._config_data = {}
        self._load_config()

    def _find_config_file(self, config_path: Optional[str]) -> Optional[Path]:
        """設定ファイルを探索"""
        if config_path:
            path = Path(config_path)
            if path.exists():
                return path
            else:
                raise ConfigError(
                    f"指定された設定ファイルが見つかりません: {config_path}"
                )

        # デフォルトの場所を探索
        possible_paths = [
            Path("config.yml"),
            Path("config.yaml"),
            Path("./config.yml"),
            Path("../config.yml"),
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # 設定ファイルが見つからない場合はNone（デフォルト値のみ使用）
        return None

    def _load_config(self):
        """設定ファイルを読み込み"""
        if self.config_path:
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config_data = yaml.safe_load(f) or {}
                print(f"✅ 設定ファイルを読み込みました: {self.config_path}")
            except yaml.YAMLError as e:
                raise ConfigError(f"設定ファイルの形式エラー: {e}")
            except Exception as e:
                raise ConfigError(f"設定ファイルの読み込みエラー: {e}")
        else:
            print("⚠️  設定ファイルが見つかりません。デフォルト値を使用します。")
            self._config_data = {}

    def get(self, key_path: str, default: Any = None) -> Any:
        """設定値を取得

        Args:
            key_path: ドット記法での設定キー（例: "openai.model"）
            default: デフォルト値

        Returns:
            設定値（環境変数 > YAML > デフォルト値の優先順位）
        """
        # 環境変数をチェック（優先度最高）
        env_value = self._get_env_value(key_path)
        if env_value is not None:
            return env_value

        # YAML設定をチェック
        yaml_value = self._get_yaml_value(key_path)
        if yaml_value is not None:
            return yaml_value

        # デフォルト値を返す
        return default

    def _get_env_value(self, key_path: str) -> Optional[Any]:
        """環境変数から値を取得"""
        # ドット記法を環境変数形式に変換
        # 例: "openai.api_key" → "OPENAI_API_KEY"
        env_key = key_path.upper().replace(".", "_")

        # 特別なマッピング
        env_mappings = {
            "OPENAI_API_KEY": "OPENAI_API_KEY",
            "OPENAI_MODEL": "OPENAI_MODEL",
        }

        # 直接的なマッピングがある場合
        if env_key in env_mappings:
            env_key = env_mappings[env_key]

        value = os.environ.get(env_key)
        if value is not None:
            # 型変換の試行
            return self._convert_type(value)

        return None

    def _get_yaml_value(self, key_path: str) -> Optional[Any]:
        """YAML設定から値を取得"""
        keys = key_path.split(".")
        current = self._config_data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _convert_type(self, value: str) -> Any:
        """文字列値を適切な型に変換"""
        # boolean
        if value.lower() in ("true", "yes", "on", "1"):
            return True
        if value.lower() in ("false", "no", "off", "0"):
            return False

        # integer
        try:
            return int(value)
        except ValueError:
            pass

        # float
        try:
            return float(value)
        except ValueError:
            pass

        # string
        return value

    def get_openai_config(self) -> Dict[str, Any]:
        """OpenAI設定を取得"""
        config = {
            "api_key": self.get("openai.api_key"),
            "model": self.get("openai.model", "gpt-4"),
            "temperature": self.get("openai.temperature", 0.7),
            "max_tokens": self.get("openai.max_tokens", 2000),
        }

        # API キーの後方互換性チェック
        if not config["api_key"]:
            config["api_key"] = os.environ.get("OPENAI_API_KEY")

        return config

    def get_debate_config(self) -> Dict[str, Any]:
        """議論設定を取得"""
        return {
            "max_rounds": self.get("debate.max_rounds", 10),
            "speaker_selection": self.get("debate.speaker_selection", "round_robin"),
            "agents": self.get(
                "debate.agents",
                {
                    "pro": {"name": "Pro", "role": "Plan A（内製）支持者"},
                    "con": {"name": "Con", "role": "Plan B（外注）支持者"},
                    "mediator": {"name": "Mediator", "role": "調停役"},
                },
            ),
        }

    def get_logging_config(self) -> Dict[str, Any]:
        """ログ設定を取得"""
        return {
            "output": {
                "enabled": self.get("logging.output.enabled", True),
                "directory": self.get("logging.output.directory", "."),
                "filename_prefix": self.get("logging.output.filename_prefix", "debate"),
                "format": self.get("logging.output.format", "markdown"),
            },
            "console": {
                "enabled": self.get("logging.console.enabled", True),
                "show_timestamps": self.get("logging.console.show_timestamps", True),
                "show_progress": self.get("logging.console.show_progress", True),
            },
        }

    def get_project_config(self) -> Dict[str, Any]:
        """プロジェクト設定を取得"""
        return {
            "name": self.get("project.name", "新規顧客向けSaaSダッシュボード開発"),
            "constraints": {
                "internal_engineers": self.get(
                    "project.constraints.internal_engineers", 2
                ),
                "monthly_hours": self.get("project.constraints.monthly_hours", 80),
                "budget_yen": self.get("project.constraints.budget_yen", 10000000),
                "deadline_months": self.get("project.constraints.deadline_months", 6),
            },
            "conditions": {
                "internal_has_domain_knowledge": self.get(
                    "project.conditions.internal_has_domain_knowledge", True
                ),
                "external_has_cloud_experience": self.get(
                    "project.conditions.external_has_cloud_experience", True
                ),
                "external_has_domain_knowledge": self.get(
                    "project.conditions.external_has_domain_knowledge", False
                ),
            },
        }

    def validate_config(self) -> bool:
        """設定の妥当性をチェック"""
        errors = []

        # OpenAI API キーのチェック
        api_key = self.get_openai_config()["api_key"]
        if not api_key:
            errors.append("OpenAI APIキーが設定されていません")

        # モデル名のチェック
        model = self.get_openai_config()["model"]
        valid_models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-5"]
        if model not in valid_models:
            errors.append(f"サポートされていないモデルです: {model}")

        if errors:
            for error in errors:
                print(f"❌ 設定エラー: {error}")
            return False

        return True

    def print_config_summary(self):
        """設定の概要を表示"""
        openai_config = self.get_openai_config()
        debate_config = self.get_debate_config()

        print("\n📋 現在の設定:")
        print(f"  OpenAI モデル: {openai_config['model']}")
        print(f"  APIキー: {'設定済み' if openai_config['api_key'] else '未設定'}")
        print(f"  最大ラウンド数: {debate_config['max_rounds']}")
        print(f"  設定ファイル: {self.config_path or 'なし（デフォルト値使用）'}")
        print()


# 後方互換性のためのグローバル関数
def load_config(config_path: Optional[str] = None) -> ConfigLoader:
    """設定ローダーを作成"""
    return ConfigLoader(config_path)


def check_openai_api_key(api_key: Optional[str]) -> bool:
    """OpenAI APIキー確認機能（後方互換性）"""
    if not api_key:
        print("❌ OpenAI APIキーが設定されていません")
        print("   環境変数 OPENAI_API_KEY を設定してください")
        print("   例: export OPENAI_API_KEY='your-api-key-here'")
        return False

    print("✅ OpenAI APIキーが設定されています")
    return True
