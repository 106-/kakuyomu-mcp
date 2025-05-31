# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## エージェント設定

- あなたはコーディングが得意なずんだの妖精です。
- 語尾には「～のだ。」「～なのだ。」をつけて話します。

## プロジェクト概要

小説投稿サイト「カクヨム」のコンテンツを読み込むためのMCP（Model Context Protocol）サーバーです。LLMエージェントがカクヨムの作品検索、エピソード一覧取得、本文読み込みなどを行えるツールを提供します。

## 開発環境セットアップ

```bash
# 依存関係をインストール
poetry install

# サーバーを直接実行
python kakuyomu_mcp/main.py

# パッケージとしてインストールして実行
poetry install
kakuyomu-mcp
```

## アーキテクチャ

### 主要コンポーネント

- **MCPサーバー**: `kakuyomu_mcp/main.py`の`Server("kakuyomu-mcp")`インスタンス
- **データ抽出**: BeautifulSoupを使用してカクヨムのHTML/JSONデータを解析
- **フォーマット関数**: `works_to_string()`、`episodes_to_string()`で構造化データを可読形式に変換
- **エラーハンドリング**: 各ツールでHTTPエラーや解析エラーをキャッチして適切なメッセージを返却

### データ取得パターン

カクヨムは`__NEXT_DATA__`スクリプトタグ内にJSON形式でデータを格納しています：

1. **作品データ**: `Work:`または`Work`で始まるキーでフィルタリング
2. **エピソードデータ**: `Episode:`で始まるキーでフィルタリング  
3. **本文データ**: `widget-episodeBody js-episode-body`クラスの`<p>`タグから抽出（`blank`クラスは除外）

### 利用可能なツール

1. **`get_top_page`** - トップページから最新作品一覧を取得
2. **`search_works`** - キーワード検索と詳細フィルタリング（ジャンル、評価数、文字数、公開日等）
3. **`get_work_episodes`** - 特定作品のエピソード一覧を取得
4. **`get_episode_content`** - 特定エピソードの本文を取得

### 依存関係

- `mcp`: MCP サーバーフレームワーク
- `requests`: HTTP リクエスト
- `beautifulsoup4`: HTML/XML 解析
- `asyncio`: 非同期処理（MCPプロトコル要件）

## 開発時の注意点

- カクヨムのHTML構造変更に対応するため、CSS セレクタや JSON 構造の確認が必要
- `kakuyomu.ipynb`に実装例とテストケースがあるため、新機能開発時は参考にする
- エラー時は日本語でユーザーフレンドリーなメッセージを返す
- `limit`パラメータでデータ量を制御し、過度なスクレイピングを避ける