#!/usr/bin/env python3
"""
Kakuyomu MCP Server

小説投稿サイト「カクヨム」のコンテンツを読み込むためのMCP (Model Context Protocol) サーバー
"""

import asyncio
import json
import logging
from typing import Any, List, Optional, Dict
import requests
from bs4 import BeautifulSoup

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("kakuyomu-mcp")


def works_to_string(data: Dict[str, Dict[str, Any]], works: List[str]) -> str:
    """作品一覧を文字列に変換"""
    output_lines: List[str] = []

    for work_id in works:
        work = data[work_id]
        
        id_ = work.get('id')
        if id_:
            output_lines.append(f"ID: {id_}")

        title = work.get('title')
        if title:
            output_lines.append(f"タイトル: {title}")

        catchphrase = work.get('catchphrase')
        if catchphrase:
            output_lines.append(f"キャッチフレーズ: {catchphrase}")

        tags = work.get('tagLabels')
        if tags:
            tag_str = ', '.join(tags)
            output_lines.append(f"タグ: {tag_str}")

        introduction = work.get('introduction')
        if introduction:
            output_lines.append("イントロダクション:\n```\n" + introduction + "\n```")
        
        output_lines.append("")  # 区切りの空行

    return '\n'.join(output_lines)


def episodes_to_string(data: Dict[str, Dict[str, Any]], episodes: List[str]) -> str:
    """エピソード一覧を文字列に変換"""
    output_lines: List[str] = []

    for episode_id in episodes:
        episode = data[episode_id]
        
        id_ = episode.get('id')
        if id_:
            output_lines.append(f"ID: {id_}")

        title = episode.get('title')
        if title:
            output_lines.append(f"タイトル: {title}")

        publishedAt = episode.get('publishedAt')
        if publishedAt:
            output_lines.append(f"公開日: {publishedAt}")
        
        output_lines.append("")  # 区切りの空行

    return '\n'.join(output_lines)


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """利用可能なツールのリストを返す"""
    return [
        types.Tool(
            name="get_top_page",
            description="カクヨムのトップページから最新作品一覧を取得",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer", 
                        "description": "取得する作品数の上限 (デフォルト: 10)",
                        "default": 10
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="search_works",
            description="カクヨムで作品を検索",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "検索キーワード"},
                    "page": {"type": "integer", "description": "ページ数 (デフォルト: 1)", "default": 1},
                    "ex_q": {"type": "string", "description": "除外キーワード (スペース区切りで複数指定可能)"},
                    "serial_status": {
                        "type": "string", 
                        "description": "連載状態", 
                        "enum": ["running", "completed"]
                    },
                    "genre_name": {
                        "type": "string",
                        "description": "作品ジャンル (カンマ区切りで複数指定可能)",
                        "enum": ["fantasy", "action", "sf", "love_story", "romance", "drama", "horror", "mystery", "nonfiction", "history", "criticism", "others", "maho", "fan_fiction"]
                    },
                    "total_review_point_range": {"type": "string", "description": "評価数範囲 (例: '1000-', '-500', 'custom')"},
                    "total_character_count_range": {"type": "string", "description": "文字数範囲 (例: '10000-', '-50000', 'custom')"},
                    "published_date_range": {
                        "type": "string",
                        "description": "作品公開日範囲",
                        "enum": ["1days", "7days", "1months", "6months", "1years", "custom"]
                    },
                    "last_episode_published_date_range": {
                        "type": "string",
                        "description": "作品更新日範囲",
                        "enum": ["1days", "7days", "1months", "6months", "1years", "custom"]
                    },
                    "limit": {
                        "type": "integer", 
                        "description": "取得する作品数の上限 (デフォルト: 10)",
                        "default": 10
                    }
                },
                "required": ["q"],
            },
        ),
        types.Tool(
            name="get_work_episodes",
            description="特定の作品のエピソード一覧を取得",
            inputSchema={
                "type": "object",
                "properties": {
                    "work_id": {"type": "string", "description": "作品ID"},
                    "limit": {
                        "type": "integer", 
                        "description": "取得するエピソード数の上限 (デフォルト: 20)",
                        "default": 20
                    }
                },
                "required": ["work_id"],
            },
        ),
        types.Tool(
            name="get_episode_content",
            description="特定のエピソードの本文を取得",
            inputSchema={
                "type": "object",
                "properties": {
                    "work_id": {"type": "string", "description": "作品ID"},
                    "episode_id": {"type": "string", "description": "エピソードID"}
                },
                "required": ["work_id", "episode_id"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> List[types.TextContent]:
    """ツール呼び出しを処理"""
    if not arguments:
        arguments = {}

    try:
        if name == "get_top_page":
            limit = arguments.get("limit", 10)
            
            url = "https://kakuyomu.jp/"
            res = requests.get(url)
            soup = BeautifulSoup(res.text, "html.parser")
            data = json.loads(soup.find("script", id="__NEXT_DATA__").string)["props"]["pageProps"]["__APOLLO_STATE__"]
            works = list(filter(lambda x: x.startswith("Work"), data.keys()))
            
            result = works_to_string(data, works[:limit])
            return [types.TextContent(type="text", text=result)]
        
        elif name == "search_works":
            q = arguments.get("q")
            page = arguments.get("page", 1)
            limit = arguments.get("limit", 10)
            
            url = "https://kakuyomu.jp/search"
            params = {"q": q, "page": str(page)}
            
            # オプションパラメータを追加
            for key in ["ex_q", "serial_status", "genre_name", "total_review_point_range", 
                       "total_character_count_range", "published_date_range", "last_episode_published_date_range"]:
                if key in arguments and arguments[key]:
                    params[key] = arguments[key]
            
            res = requests.get(url, params=params)
            soup = BeautifulSoup(res.text, "html.parser")
            data = json.loads(soup.find("script", id="__NEXT_DATA__").string)["props"]["pageProps"]["__APOLLO_STATE__"]
            works = list(filter(lambda x: x.startswith("Work:"), data.keys()))
            
            result = works_to_string(data, works[:limit])
            return [types.TextContent(type="text", text=result)]
        
        elif name == "get_work_episodes":
            work_id = arguments.get("work_id")
            limit = arguments.get("limit", 20)
            
            url = f"https://kakuyomu.jp/works/{work_id}"
            res = requests.get(url)
            soup = BeautifulSoup(res.text, "html.parser")
            data = json.loads(soup.find("script", id="__NEXT_DATA__").string)["props"]["pageProps"]["__APOLLO_STATE__"]
            episodes = list(filter(lambda x: x.startswith("Episode:"), data.keys()))
            
            result = episodes_to_string(data, episodes[:limit])
            return [types.TextContent(type="text", text=result)]
        
        elif name == "get_episode_content":
            work_id = arguments.get("work_id")
            episode_id = arguments.get("episode_id")
            
            url = f"https://kakuyomu.jp/works/{work_id}/episodes/{episode_id}"
            res = requests.get(url)
            soup = BeautifulSoup(res.text, "html.parser")
            
            episode_body = soup.find("div", class_="widget-episodeBody js-episode-body")
            if not episode_body:
                return [types.TextContent(type="text", text="エピソードの本文が見つかりませんでした。")]
            
            # class="blank" を除いた <p> タグのテキストだけ抽出
            paragraphs = [
                p.get_text(strip=True)
                for p in episode_body.find_all("p")
                if "blank" not in p.get("class", [])
            ]
            
            episode_content = "\n".join(paragraphs)
            return [types.TextContent(type="text", text=episode_content)]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}")
        return [types.TextContent(type="text", text=f"エラーが発生しました: {str(e)}")]


@server.list_resources()
async def handle_list_resources() -> List[types.Resource]:
    """利用可能なリソースのリストを返す"""
    return [
        types.Resource(
            uri="info://kakuyomu-server",
            name="Kakuyomu MCP Server Information",
            description="カクヨムMCPサーバーについての情報",
            mimeType="text/plain",
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """リソースを読み込む"""
    if uri == "info://kakuyomu-server":
        return """カクヨム MCP サーバー

小説投稿サイト「カクヨム」のコンテンツを読み込むためのMCPサーバーです。

利用可能なツール:
1. get_top_page - トップページから最新作品一覧を取得
2. search_works - 作品を検索
3. get_work_episodes - 作品のエピソード一覧を取得
4. get_episode_content - エピソードの本文を取得
"""
    else:
        raise ValueError(f"Unknown resource: {uri}")


async def main():
    """メインエントリーポイント"""
    logger.info("Starting Kakuyomu MCP server")
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="kakuyomu-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())