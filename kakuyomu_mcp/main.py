#!/usr/bin/env python3
"""
Kakuyomu MCP Server

小説投稿サイト「カクヨム」のコンテンツを読み込むためのMCP (Model Context Protocol) サーバー
"""

import argparse
import os
import json
import logging
from typing import Any, List, Dict
import requests
from bs4 import BeautifulSoup

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

host = os.getenv("HOST", "127.0.0.1")
port = int(os.getenv("PORT", 9468))
mcp = FastMCP("kakuyomu-mcp", host=host, port=port)


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


@mcp.tool()
def get_top_page(limit: int = 10) -> str:
    """カクヨムのトップページから最新作品一覧を取得"""
    try:
        soup = kakuyomu_request("https://kakuyomu.jp/")
        data = parse_apollo_data(soup)
        works = list(filter(lambda x: x.startswith("Work"), data.keys()))
        return works_to_string(data, works[:limit])
    except Exception as e:
        logger.error(f"Error in get_top_page: {str(e)}")
        return f"エラーが発生しました: {str(e)}"


@mcp.tool()
def search_works(
    q: str,
    page: int = 1,
    ex_q: str = None,
    serial_status: str = None,
    genre_name: str = None,
    total_review_point_range: str = None,
    total_character_count_range: str = None,
    published_date_range: str = None,
    last_episode_published_date_range: str = None,
    limit: int = 10,
) -> str:
    """カクヨムで作品を検索"""
    try:
        params = {"q": q, "page": str(page)}

        # オプションパラメータを追加
        optional_params = {
            "ex_q": ex_q,
            "serial_status": serial_status,
            "genre_name": genre_name,
            "total_review_point_range": total_review_point_range,
            "total_character_count_range": total_character_count_range,
            "published_date_range": published_date_range,
            "last_episode_published_date_range": last_episode_published_date_range,
        }

        for key, value in optional_params.items():
            if value:
                params[key] = value

        soup = kakuyomu_request("https://kakuyomu.jp/search", params)
        data = parse_apollo_data(soup)
        works = list(filter(lambda x: x.startswith("Work:"), data.keys()))
        return works_to_string(data, works[:limit])
    except Exception as e:
        logger.error(f"Error in search_works: {str(e)}")
        return f"エラーが発生しました: {str(e)}"


@mcp.tool()
def get_work_episodes(work_id: str, limit: int = 20) -> str:
    """特定の作品のエピソード一覧を取得"""
    try:
        soup = kakuyomu_request(f"https://kakuyomu.jp/works/{work_id}")
        data = parse_apollo_data(soup)
        episodes = list(filter(lambda x: x.startswith("Episode:"), data.keys()))
        return episodes_to_string(data, episodes[:limit])
    except Exception as e:
        logger.error(f"Error in get_work_episodes: {str(e)}")
        return f"エラーが発生しました: {str(e)}"


@mcp.tool()
def get_episode_content(work_id: str, episode_id: str) -> str:
    """特定のエピソードの本文を取得"""
    try:
        soup = kakuyomu_request(
            f"https://kakuyomu.jp/works/{work_id}/episodes/{episode_id}"
        )

        episode_body = soup.find("div", class_="widget-episodeBody js-episode-body")
        if not episode_body:
            return "エピソードの本文が見つかりませんでした。"

        # class="blank" を除いた <p> タグのテキストだけ抽出
        paragraphs = [
            p.get_text(strip=True)
            for p in episode_body.find_all("p")
            if "blank" not in p.get("class", [])
        ]

        return "\n".join(paragraphs)
    except Exception as e:
        logger.error(f"Error in get_episode_content: {str(e)}")
        return f"エラーが発生しました: {str(e)}"


@mcp.tool()
def get_rankings(genre: str = "all", period: str = "daily", limit: int = 10) -> str:
    """カクヨムのランキングページから作品ランキングを取得"""
    try:
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
            author_link = work_element.find("a", class_="widget-workCard-authorLabel")
            if author_link:
                ranking_data["author"] = author_link.get_text(strip=True)

            # キャッチフレーズを取得（最初のレビューから）
            catchphrase_element = work_element.find("a", itemprop="reviewBody")
            if catchphrase_element:
                ranking_data["catchphrase"] = catchphrase_element.get_text(strip=True)

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

        return rankings_to_string(rankings)
    except Exception as e:
        logger.error(f"Error in get_rankings: {str(e)}")
        return f"エラーが発生しました: {str(e)}"


@mcp.resource("info://kakuyomu-server")
def get_server_info() -> str:
    """カクヨムMCPサーバーについての情報"""
    return """カクヨム MCP サーバー

小説投稿サイト「カクヨム」のコンテンツを読み込むためのMCPサーバーです。

利用可能なツール:
1. get_top_page - トップページから最新作品一覧を取得
2. search_works - 作品を検索
3. get_work_episodes - 作品のエピソード一覧を取得
4. get_episode_content - エピソードの本文を取得
5. get_rankings - ランキングページから作品ランキングを取得
"""


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="カクヨムMCPサーバー - 小説投稿サイト「カクヨム」のコンテンツを読み込むMCPサーバー",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""使用例:
  %(prog)s --transport stdio          # stdioモードで起動 (デフォルト)
  %(prog)s --transport streamable-http # HTTPモードで起動""",
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="トランスポート方式 (デフォルト: stdio)",
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        logger.info("Starting Kakuyomu MCP server with stdio transport")
        mcp.run(transport="stdio")
    else:
        logger.info("Starting Kakuyomu MCP server with streamable-http transport")
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
