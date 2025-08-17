"""
CLI引数パーサーモジュール

Clickライブラリを使用してCLI引数を定義し、パースします。
設定の優先順位：CLI引数 > 環境変数 > config.yml > デフォルト値
"""

import click
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Python 3.11以降はtomllib、それ以前はtomliを使用
try:
    import tomllib
except ImportError:
    import tomli as tomllib

from .config import ConfigLoader, ConfigError


def get_version() -> str:
    """pyproject.tomlからバージョン情報を取得"""
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("version", "unknown")
    except Exception:
        return "unknown"


class CLIConfig:
    """CLI設定を管理するクラス

    CLI引数を最高優先度として、ConfigLoaderと連携して
    最終的な設定を提供します。
    """

    def __init__(self, cli_args: Dict[str, Any]):
        """初期化

        Args:
            cli_args: CLI引数の辞書
        """
        self.cli_args = cli_args
        self.config_loader = None
        self._load_config_file()

    def _load_config_file(self):
        """設定ファイルを読み込み"""
        config_path = self.cli_args.get("config")
        try:
            self.config_loader = ConfigLoader(config_path)
        except ConfigError as e:
            click.echo(f"❌ 設定ファイルエラー: {e}", err=True)
            sys.exit(1)

    def get(self, key_path: str, default: Any = None) -> Any:
        """設定値を取得

        優先順位：CLI引数 > 環境変数 > config.yml > デフォルト値

        Args:
            key_path: ドット記法での設定キー
            default: デフォルト値

        Returns:
            設定値
        """
        # CLI引数をチェック（最高優先度）
        cli_value = self._get_cli_value(key_path)
        if cli_value is not None:
            return cli_value

        # ConfigLoaderに委譲（環境変数 > YAML > デフォルト値の順）
        if self.config_loader:
            return self.config_loader.get(key_path, default)

        return default

    def _get_cli_value(self, key_path: str) -> Optional[Any]:
        """CLI引数から値を取得"""
        # ドット記法をCLI引数名に変換
        # 例: "openai.api_key" → "api_key"
        #     "openai.model" → "model"
        #     "debate.max_rounds" → "rounds"

        cli_mappings = {
            "openai.api_key": "api_key",
            "openai.model": "model",
            "openai.temperature": "temperature",
            "openai.max_tokens": "max_tokens",
            "debate.max_rounds": "rounds",
            "project.language": "language",
            "logging.output.directory": "output_dir",
            "logging.console.enabled": "verbose",
        }

        cli_key = cli_mappings.get(key_path)
        if cli_key and cli_key in self.cli_args:
            value = self.cli_args[cli_key]
            # Noneまたは未設定の場合は無視
            if value is not None:
                return value

        return None

    def get_openai_config(self) -> Dict[str, Any]:
        """OpenAI設定を取得（CLI引数を最優先）"""
        return {
            "api_key": self.get("openai.api_key"),
            "model": self.get("openai.model", "gpt-4"),
            "temperature": self.get("openai.temperature", 0.7),
            "max_tokens": self.get("openai.max_tokens", 2000),
        }

    def get_debate_config(self) -> Dict[str, Any]:
        """議論設定を取得（CLI引数を最優先）"""
        config = {}
        if self.config_loader:
            config = self.config_loader.get_debate_config()

        # CLI引数で上書き
        rounds = self.get("debate.max_rounds")
        if rounds is not None:
            config["max_rounds"] = rounds

        return config

    def get_logging_config(self) -> Dict[str, Any]:
        """ログ設定を取得（CLI引数を最優先）"""
        config = {}
        if self.config_loader:
            config = self.config_loader.get_logging_config()

        # CLI引数で上書き
        output_dir = self.get("logging.output.directory")
        if output_dir is not None:
            config["output"]["directory"] = output_dir

        verbose = self.get("logging.console.enabled")
        if verbose is not None:
            config["console"]["enabled"] = verbose

        return config

    def get_project_config(self) -> Dict[str, Any]:
        """プロジェクト設定を取得（CLI引数を最優先）"""
        config = {}
        if self.config_loader:
            config = self.config_loader.get_project_config()

        # CLI引数で上書き
        language = self.get("project.language")
        if language is not None:
            config["language"] = language

        return config

    def validate_config(self) -> bool:
        """設定の妥当性をチェック"""
        errors = []

        # OpenAI API キーのチェック
        api_key = self.get_openai_config()["api_key"]
        if not api_key:
            errors.append("OpenAI APIキーが設定されていません")

        # モデル名のチェック
        model = self.get_openai_config()["model"]
        valid_models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o", "gpt-5"]
        if model not in valid_models:
            errors.append(f"サポートされていないモデルです: {model}")

        # 議論回数のチェック
        rounds = self.get("debate.max_rounds", 10)
        if not isinstance(rounds, int) or rounds < 1 or rounds > 100:
            errors.append(f"議論回数は1〜100の範囲で指定してください: {rounds}")

        # 温度設定のチェック
        temperature = self.get("openai.temperature", 0.7)
        if (
            not isinstance(temperature, (int, float))
            or temperature < 0.0
            or temperature > 2.0
        ):
            errors.append(f"温度設定は0.0〜2.0の範囲で指定してください: {temperature}")

        # 最大トークン数のチェック
        max_tokens = self.get("openai.max_tokens", 2000)
        if not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > 32000:
            errors.append(
                f"最大トークン数は1〜32000の範囲で指定してください: {max_tokens}"
            )

        # 言語設定のチェック
        language = self.get("project.language", "ja")
        valid_languages = ["ja", "en", "zh"]
        if language not in valid_languages:
            errors.append(f"サポートされていない言語です: {language}")

        if errors:
            for error in errors:
                click.echo(f"❌ 設定エラー: {error}", err=True)
            return False

        return True

    def print_config_summary(self, show_dry_run: bool = False):
        """設定の概要を表示"""
        openai_config = self.get_openai_config()
        debate_config = self.get_debate_config()
        project_config = self.get_project_config()
        logging_config = self.get_logging_config()

        if show_dry_run:
            click.echo("\n🔍 Dry Run - 設定内容確認:")
        else:
            click.echo("\n📋 現在の設定:")

        click.echo(f"  OpenAI モデル: {openai_config['model']}")
        click.echo(f"  APIキー: {'設定済み' if openai_config['api_key'] else '未設定'}")
        click.echo(f"  温度設定: {openai_config['temperature']}")
        click.echo(f"  最大トークン数: {openai_config['max_tokens']}")
        click.echo(f"  議論回数: {debate_config.get('max_rounds', 10)}")
        click.echo(f"  言語設定: {project_config.get('language', 'ja')}")
        click.echo(f"  出力ディレクトリ: {logging_config['output']['directory']}")
        click.echo(
            f"  詳細ログ: {'有効' if logging_config['console']['enabled'] else '無効'}"
        )
        click.echo(
            f"  設定ファイル: {self.config_loader.config_path if self.config_loader and self.config_loader.config_path else 'なし（デフォルト値使用）'}"
        )

        if show_dry_run:
            click.echo("\n✅ 設定確認完了。実際の実行は行いません。")
        else:
            click.echo()


def validate_temperature(ctx, param, value):
    """温度設定のバリデーション"""
    if value is not None and (value < 0.0 or value > 2.0):
        raise click.BadParameter("温度設定は0.0〜2.0の範囲で指定してください")
    return value


def validate_rounds(ctx, param, value):
    """議論回数のバリデーション"""
    if value is not None and (value < 1 or value > 100):
        raise click.BadParameter("議論回数は1〜100の範囲で指定してください")
    return value


def validate_max_tokens(ctx, param, value):
    """最大トークン数のバリデーション"""
    if value is not None and (value < 1 or value > 32000):
        raise click.BadParameter("最大トークン数は1〜32000の範囲で指定してください")
    return value


def validate_language(ctx, param, value):
    """言語設定のバリデーション"""
    if value is not None and value not in ["ja", "en", "zh"]:
        raise click.BadParameter("サポートされている言語: ja, en, zh")
    return value


@click.command()
@click.argument("topic", required=False)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True),
    help="設定ファイルのパス [default: config.yml]",
)
@click.option("--api-key", help="OpenAI APIキー")
@click.option("--model", help="使用するAIモデル")
@click.option(
    "--rounds", type=int, callback=validate_rounds, help="議論の回数 [default: 10]"
)
@click.option(
    "--temperature",
    type=float,
    callback=validate_temperature,
    help="AIの創造性設定 [0.0-2.0]",
)
@click.option(
    "--max-tokens", type=int, callback=validate_max_tokens, help="最大トークン数"
)
@click.option("--language", callback=validate_language, help="議論言語 [ja/en/zh]")
@click.option("--output-dir", type=click.Path(), help="出力ディレクトリ")
@click.option("--verbose", is_flag=True, help="詳細ログ出力を有効化")
@click.option("--dry-run", is_flag=True, help="設定内容の確認のみ実行")
@click.version_option(version=get_version(), message="%(prog)s version %(version)s")
def main(
    topic,
    config,
    api_key,
    model,
    rounds,
    temperature,
    max_tokens,
    language,
    output_dir,
    verbose,
    dry_run,
):
    """
    OWLS - AI議論システム

    複数のAIエージェントによる議論を実行します。

    TOPIC: 議論のトピック（未指定の場合はデフォルトトピックを使用）

    Examples:

        # デフォルト設定で実行
        python main.py "新機能の開発方針について"

        # 設定を指定して実行
        python main.py --rounds 5 --temperature 0.5 "プロジェクト計画"

        # 設定確認のみ
        python main.py --dry-run
    """

    # CLI引数を辞書にまとめる
    cli_args = {
        "topic": topic,
        "config": config,
        "api_key": api_key,
        "model": model,
        "rounds": rounds,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "language": language,
        "output_dir": output_dir,
        "verbose": verbose,
        "dry_run": dry_run,
    }

    # CLIConfigを作成
    cli_config = CLIConfig(cli_args)

    # Dry runの場合は設定確認のみ
    if dry_run:
        cli_config.print_config_summary(show_dry_run=True)
        return cli_config

    # 設定の妥当性チェック
    if not cli_config.validate_config():
        click.echo("\n🔧 解決方法:", err=True)
        click.echo("1. OpenAIのAPIキーを取得", err=True)
        click.echo("2. 環境変数を設定: export OPENAI_API_KEY='your-api-key'", err=True)
        click.echo("3. または --api-key オプションで指定", err=True)
        click.echo("4. または config.yml の openai.api_key を設定", err=True)
        sys.exit(1)

    # 設定概要を表示
    cli_config.print_config_summary()

    return cli_config


if __name__ == "__main__":
    main()
