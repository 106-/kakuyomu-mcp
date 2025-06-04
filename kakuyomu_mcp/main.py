#!/usr/bin/env python3
"""
Kakuyomu MCP Server

小説投稿サイト「カクヨム」のコンテンツを読み込むためのMCP (Model Context Protocol) サーバー
"""

import asyncio
import json
import logging
from typing import Any, List, Dict
import requests
from bs4 import BeautifulSoup

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("kakuyomu-mcp")

# ツール定義のinputSchema
TOOL_SCHEMAS = {
    "get_top_page": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "取得する作品数の上限 (デフォルト: 10)",
                "default": 10,
            }
        },
        "required": [],
    },
    "search_works": {
        "type": "object",
        "properties": {
            "q": {"type": "string", "description": "検索キーワード"},
            "page": {
                "type": "integer",
                "description": "ページ数 (デフォルト: 1)",
                "default": 1,
            },
            "ex_q": {
                "type": "string",
                "description": "除外キーワード (スペース区切りで複数指定可能)",
            },
            "serial_status": {
                "type": "string",
                "description": "連載状態",
                "enum": ["running", "completed"],
            },
            "genre_name": {
                "type": "string",
                "description": "作品ジャンル (カンマ区切りで複数指定可能)",
                "enum": [
                    "fantasy",
                    "action",
                    "sf",
                    "love_story",
                    "romance",
                    "drama",
                    "horror",
                    "mystery",
                    "nonfiction",
                    "history",
                    "criticism",
                    "others",
                    "maho",
                    "fan_fiction",
                ],
            },
            "total_review_point_range": {
                "type": "string",
                "description": "評価数範囲 (例: '1000-', '-500', 'custom')",
            },
            "total_character_count_range": {
                "type": "string",
                "description": "文字数範囲 (例: '10000-', '-50000', 'custom')",
            },
            "published_date_range": {
                "type": "string",
                "description": "作品公開日範囲",
                "enum": [
                    "1days",
                    "7days",
                    "1months",
                    "6months",
                    "1years",
                    "custom",
                ],
            },
            "last_episode_published_date_range": {
                "type": "string",
                "description": "作品更新日範囲",
                "enum": [
                    "1days",
                    "7days",
                    "1months",
                    "6months",
                    "1years",
                    "custom",
                ],
            },
            "limit": {
                "type": "integer",
                "description": "取得する作品数の上限 (デフォルト: 10)",
                "default": 10,
            },
        },
        "required": ["q"],
    },
    "get_work_episodes": {
        "type": "object",
        "properties": {
            "work_id": {"type": "string", "description": "作品ID"},
            "limit": {
                "type": "integer",
                "description": "取得するエピソード数の上限 (デフォルト: 20)",
                "default": 20,
            },
        },
        "required": ["work_id"],
    },
    "get_episode_content": {
        "type": "object",
        "properties": {
            "work_id": {"type": "string", "description": "作品ID"},
            "episode_id": {"type": "string", "description": "エピソードID"},
        },
        "required": ["work_id", "episode_id"],
    },
    "get_rankings": {
        "type": "object",
        "properties": {
            "genre": {
                "type": "string",
                "description": "ジャンル",
                "enum": [
                    "all",
                    "fantasy",
                    "action",
                    "sf",
                    "love_story",
                    "romance",
                    "drama",
                    "horror",
                    "mystery",
                    "nonfiction",
                    "history",
                    "criticism",
                    "others",
                ],
                "default": "all",
            },
            "period": {
                "type": "string",
                "description": "期間",
                "enum": ["daily", "weekly", "monthly", "yearly", "entire"],
                "default": "daily",
            },
            "limit": {
                "type": "integer",
                "description": "取得する作品数の上限 (デフォルト: 10)",
                "default": 10,
            },
        },
        "required": [],
    },
}


def kakuyomu_request(url: str, params: dict = None) -> BeautifulSoup:
    """カクヨムのページを取得してBeautifulSoupオブジェクトを返す"""
    res = requests.get(url, params=params)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def parse_apollo_data(soup: BeautifulSoup) -> Dict[str, Any]:
    """__NEXT_DATA__からApollo状態データを抽出"""
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if not script_tag:
        raise ValueError("__NEXT_DATA__スクリプトタグが見つかりません")
    
    data = json.loads(script_tag.string)
    return data["props"]["pageProps"]["__APOLLO_STATE__"]


def works_to_string(data: Dict[str, Dict[str, Any]], works: List[str]) -> str:
    """作品一覧を文字列に変換"""
    output_lines: List[str] = []

    for work_id in works:
        work = data[work_id]

        id_ = work.get("id")
        if id_:
            output_lines.append(f"ID: {id_}")

        title = work.get("title")
        if title:
            output_lines.append(f"タイトル: {title}")

        catchphrase = work.get("catchphrase")
        if catchphrase:
            output_lines.append(f"キャッチフレーズ: {catchphrase}")

        tags = work.get("tagLabels")
        if tags:
            tag_str = ", ".join(tags)
            output_lines.append(f"タグ: {tag_str}")

        introduction = work.get("introduction")
        if introduction:
            output_lines.append("イントロダクション:\n```\n" + introduction + "\n```")

        output_lines.append("")  # 区切りの空行

    return "\n".join(output_lines)


def episodes_to_string(data: Dict[str, Dict[str, Any]], episodes: List[str]) -> str:
    """エピソード一覧を文字列に変換"""
    output_lines: List[str] = []

    for episode_id in episodes:
        episode = data[episode_id]

        id_ = episode.get("id")
        if id_:
            output_lines.append(f"ID: {id_}")

        title = episode.get("title")
        if title:
            output_lines.append(f"タイトル: {title}")

        publishedAt = episode.get("publishedAt")
        if publishedAt:
            output_lines.append(f"公開日: {publishedAt}")

        output_lines.append("")  # 区切りの空行

    return "\n".join(output_lines)


def rankings_to_string(rankings: List[Dict[str, Any]]) -> str:
    """ランキングデータを文字列に変換"""
    output_lines: List[str] = []

    for ranking_data in rankings:
        rank = ranking_data.get("rank")
        if rank:
            output_lines.append(f"順位: {rank}")

        id_ = ranking_data.get("id")
        if id_:
            output_lines.append(f"ID: {id_}")

        title = ranking_data.get("title")
        if title:
            output_lines.append(f"タイトル: {title}")

        author = ranking_data.get("author")
        if author:
            output_lines.append(f"作者: {author}")

        catchphrase = ranking_data.get("catchphrase")
        if catchphrase:
            output_lines.append(f"キャッチフレーズ: {catchphrase}")

        tags = ranking_data.get("tags")
        if tags:
            tag_str = ", ".join(tags)
            output_lines.append(f"タグ: {tag_str}")

        introduction = ranking_data.get("introduction")
        if introduction:
            output_lines.append("イントロダクション:\n```\n" + introduction + "\n```")

        output_lines.append("")  # 区切りの空行

    return "\n".join(output_lines)


def handle_get_top_page(arguments: dict) -> List[types.TextContent]:
    """トップページから最新作品一覧を取得"""
    limit = arguments.get("limit", 10)
    
    soup = kakuyomu_request("https://kakuyomu.jp/")
    data = parse_apollo_data(soup)
    works = list(filter(lambda x: x.startswith("Work"), data.keys()))
    
    result = works_to_string(data, works[:limit])
    return [types.TextContent(type="text", text=result)]


def handle_search_works(arguments: dict) -> List[types.TextContent]:
    """作品を検索"""
    q = arguments.get("q")
    page = arguments.get("page", 1)
    limit = arguments.get("limit", 10)
    
    params = {"q": q, "page": str(page)}
    
    # オプションパラメータを追加
    for key in [
        "ex_q",
        "serial_status",
        "genre_name",
        "total_review_point_range",
        "total_character_count_range",
        "published_date_range",
        "last_episode_published_date_range",
    ]:
        if key in arguments and arguments[key]:
            params[key] = arguments[key]
    
    soup = kakuyomu_request("https://kakuyomu.jp/search", params)
    data = parse_apollo_data(soup)
    works = list(filter(lambda x: x.startswith("Work:"), data.keys()))
    
    result = works_to_string(data, works[:limit])
    return [types.TextContent(type="text", text=result)]


def handle_get_work_episodes(arguments: dict) -> List[types.TextContent]:
    """特定の作品のエピソード一覧を取得"""
    work_id = arguments.get("work_id")
    limit = arguments.get("limit", 20)
    
    soup = kakuyomu_request(f"https://kakuyomu.jp/works/{work_id}")
    data = parse_apollo_data(soup)
    episodes = list(filter(lambda x: x.startswith("Episode:"), data.keys()))
    
    result = episodes_to_string(data, episodes[:limit])
    return [types.TextContent(type="text", text=result)]


def handle_get_episode_content(arguments: dict) -> List[types.TextContent]:
    """特定のエピソードの本文を取得"""
    work_id = arguments.get("work_id")
    episode_id = arguments.get("episode_id")
    
    soup = kakuyomu_request(f"https://kakuyomu.jp/works/{work_id}/episodes/{episode_id}")
    
    episode_body = soup.find("div", class_="widget-episodeBody js-episode-body")
    if not episode_body:
        return [
            types.TextContent(
                type="text", text="エピソードの本文が見つかりませんでした。"
            )
        ]
    
    # class="blank" を除いた <p> タグのテキストだけ抽出
    paragraphs = [
        p.get_text(strip=True)
        for p in episode_body.find_all("p")
        if "blank" not in p.get("class", [])
    ]
    
    episode_content = "\n".join(paragraphs)
    return [types.TextContent(type="text", text=episode_content)]


def handle_get_rankings(arguments: dict) -> List[types.TextContent]:
    """ランキングページから作品ランキングを取得"""
    genre = arguments.get("genre", "all")
    period = arguments.get("period", "daily")
    limit = arguments.get("limit", 10)
    
    soup = kakuyomu_request(f"https://kakuyomu.jp/rankings/{genre}/{period}")
    
    # ランキングの作品要素を取得
    work_elements = soup.find_all("div", class_="widget-work float-parent")
    
    rankings = []
    for work_element in work_elements[:limit]:
        ranking_data = {}
        
        # 順位を取得
        rank_element = work_element.find("p", class_="widget-work-rank")
        if rank_element:
            ranking_data["rank"] = rank_element.get_text(strip=True)
        
        # 作品IDを取得（URLから抽出）
        title_link = work_element.find("a", class_="widget-workCard-titleLabel")
        if title_link and title_link.get("href"):
            href = title_link.get("href")
            work_id = href.split("/works/")[-1] if "/works/" in href else None
            if work_id:
                ranking_data["id"] = work_id
        
        # タイトルを取得
        if title_link:
            ranking_data["title"] = title_link.get_text(strip=True)
        
        # 作者を取得
        author_link = work_element.find(
            "a", class_="widget-workCard-authorLabel"
        )
        if author_link:
            ranking_data["author"] = author_link.get_text(strip=True)
        
        # キャッチフレーズを取得（最初のレビューから）
        catchphrase_element = work_element.find("a", itemprop="reviewBody")
        if catchphrase_element:
            ranking_data["catchphrase"] = catchphrase_element.get_text(
                strip=True
            )
        
        # タグを取得
        tag_elements = work_element.find_all(
            "a", href=lambda x: x and "/tags/" in x
        )
        if tag_elements:
            tags = [
                tag.find("span").get_text(strip=True)
                for tag in tag_elements
                if tag.find("span")
            ]
            ranking_data["tags"] = tags
        
        # イントロダクションを取得
        intro_element = work_element.find(
            "p", class_="widget-workCard-introduction"
        )
        if intro_element:
            intro_link = intro_element.find("a")
            if intro_link:
                ranking_data["introduction"] = intro_link.get_text(strip=True)
        
        rankings.append(ranking_data)
    
    result = rankings_to_string(rankings)
    return [types.TextContent(type="text", text=result)]


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """利用可能なツールのリストを返す"""
    return [
        types.Tool(
            name="get_top_page",
            description="カクヨムのトップページから最新作品一覧を取得",
            inputSchema=TOOL_SCHEMAS["get_top_page"],
        ),
        types.Tool(
            name="search_works",
            description="カクヨムで作品を検索",
            inputSchema=TOOL_SCHEMAS["search_works"],
        ),
        types.Tool(
            name="get_work_episodes",
            description="特定の作品のエピソード一覧を取得",
            inputSchema=TOOL_SCHEMAS["get_work_episodes"],
        ),
        types.Tool(
            name="get_episode_content",
            description="特定のエピソードの本文を取得",
            inputSchema=TOOL_SCHEMAS["get_episode_content"],
        ),
        types.Tool(
            name="get_rankings",
            description="カクヨムのランキングページから作品ランキングを取得",
            inputSchema=TOOL_SCHEMAS["get_rankings"],
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
        match name:
            case "get_top_page":
                return handle_get_top_page(arguments)
            case "search_works":
                return handle_search_works(arguments)
            case "get_work_episodes":
                return handle_get_work_episodes(arguments)
            case "get_episode_content":
                return handle_get_episode_content(arguments)
            case "get_rankings":
                return handle_get_rankings(arguments)
            case _:
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
5. get_rankings - ランキングページから作品ランキングを取得
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
