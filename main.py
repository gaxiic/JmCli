from astrbot.api.message_components import File, Image, Plain
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.all import *

import asyncio
import os
import glob
import random

import jmcomic
from jmcomic import JmMagicConstants

@register("JmCli", "Gaxiic", "JM命令行工具，实现了5个功能：根据ID下载、根据ID查询、根据关键词查询、根据作者查询、随机推荐，输入jm_help查看用法", "1.0.0")
class JMPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.downloading = set()
        self.downloading_covers = set()
        self.base_path = os.path.abspath(os.path.dirname(__file__))
        self.option = self._load_config()

    def _load_config(self):
        return jmcomic.create_option_by_file(os.path.join(self.base_path, "option.yml"))

    async def _get_client(self):
        return self.option.new_jm_client()

    def _get_cover_path(self, album_id):
        return os.path.join(self.base_path, "picture", str(album_id), "00001.jpg")

    def _get_total_pages(self, client, album):
        return sum(len(client.get_photo_detail(p.photo_id, False)) for p in album)

    async def _download_cover(self, album_id):
        if album_id in self.downloading_covers:
            return False, "封面正在下载"
        
        self.downloading_covers.add(album_id)
        try:
            client = await self._get_client()
            album = client.get_album_detail(album_id)
            if not album or not album:
                return False, "本子不存在"
            
            first_photo = album[0]
            photo = client.get_photo_detail(first_photo.photo_id, True)
            if not photo or not photo:
                return False, "章节内容为空"
            
            image = photo[0]
            cover_dir = os.path.join(self.base_path, "picture", str(album_id))
            os.makedirs(cover_dir, exist_ok=True)
            
            cover_path = self._get_cover_path(album_id)
            client.download_by_image_detail(image, cover_path)
            return True, cover_path
        except Exception as e:
            return False, f"封面下载失败: {str(e)}"
        finally:
            self.downloading_covers.discard(album_id)

    async def _download_album(self, album_id):
        if album_id in self.downloading:
            return False, "下载中，请稍后"
            
        self.downloading.add(album_id)
        try:
            await asyncio.to_thread(jmcomic.download_album, album_id, self.option)
            return True, None
        except Exception as e:
            return False, f"下载失败: {str(e)}"
        finally:
            self.downloading.discard(album_id)

    async def _build_album_message(self, client, album, album_id, cover_path):
        total_pages = self._get_total_pages(client, album)
        message = (
            f"📖: {album.title}\n"
            f"🆔: {album_id}\n"
            f"🏷️: {', '.join(album.tags[:5])}\n"
            f"📅: {getattr(album, 'pub_date', '未知')}\n"
            f"📃: {total_pages}"
        )
        return [Plain(text=message), Image.fromFileSystem(cover_path)]

    @filter.command("jm")
    async def get_comic_detail(self, event: AstrMessageEvent):
        parts = event.message_str.strip().split()
        if len(parts) < 2:
            return event.plain_result("格式: /jm [本子ID]")
        
        album_id = parts[1]
        client = await self._get_client()
        
        try:
            album = client.get_album_detail(album_id)
            cover_path = self._get_cover_path(album_id)
            
            if not os.path.exists(cover_path):
                success, result = await self._download_cover(album_id)
                if not success:
                    return event.plain_result(f"{album.title}\n封面下载失败: {result}")
                cover_path = result
            
            return event.chain_result(await self._build_album_message(client, album, album_id, cover_path))
        except Exception as e:
            return event.plain_result(f"获取失败: {str(e)}")

    @filter.command("jm下载")
    async def download_comic(self, event: AstrMessageEvent):
        parts = event.message_str.strip().split()
        if len(parts) < 2:
            return event.plain_result("格式: /jm下载 [本子ID]")
        
        album_id = parts[1]
        pdf_path = os.path.join(self.base_path, "pdf", f"{album_id}.pdf")
        
        if os.path.exists(pdf_path):
            return event.chain_result([File(name=f"{album_id}.pdf", file=pdf_path)])
        
        success, msg = await self._download_album(album_id)
        if not success:
            return event.plain_result(msg)
        
        pdf_files = glob.glob(f"{self.base_path}/pdf/*.pdf")
        if not pdf_files:
            return event.plain_result("PDF生成失败")
        
        os.rename(max(pdf_files, key=os.path.getctime), pdf_path)
        return event.chain_result([File(name=f"{album_id}.pdf", file=pdf_path)])

    @filter.command("jm推荐")
    async def recommend_comic(self, event: AstrMessageEvent):
        client = await self._get_client()
        try:
            ranking = client.month_ranking(1)
            album_id, _ = random.choice(list(ranking.iter_id_title()))
            album = client.get_album_detail(album_id)
            
            cover_path = self._get_cover_path(album_id)
            if not os.path.exists(cover_path):
                success, result = await self._download_cover(album_id)
                if not success:
                    return event.plain_result(f"{album.title}\n封面下载失败")
                cover_path = result
            
            return event.chain_result(await self._build_album_message(client, album, album_id, cover_path))
        except Exception as e:
            return event.plain_result(f"推荐失败: {str(e)}")

    @filter.command("jm搜索")
    async def search_comic(self, event: AstrMessageEvent):
        parts = event.message_str.strip().split()
        if len(parts) < 3:
            return event.plain_result("格式: /jm搜索 [关键词] [序号]")
        
        *keywords, order = parts[1:]
        try:
            order = int(order)
            if order < 1:
                return event.plain_result("序号必须≥1")
        except:
            return event.plain_result("序号必须是数字")
        
        client = await self._get_client()
        search_query = ' '.join(f'+{k}' for k in keywords)
        
        results = []
        for page in range(1, 4):
            results.extend(list(client.search_site(search_query, page).iter_id_title()))
            if len(results) >= order:
                break
        
        if len(results) < order:
            return event.plain_result(f"仅找到{len(results)}条结果")
        
        album_id, _ = results[order-1]
        album = client.get_album_detail(album_id)
        
        cover_path = self._get_cover_path(album_id)
        if not os.path.exists(cover_path):
            success, result = await self._download_cover(album_id)
            if not success:
                return event.plain_result(f"{album.title}\n封面下载失败")
            cover_path = result
        
        return event.chain_result(await self._build_album_message(client, album, album_id, cover_path))

    @filter.command("jm作者")
    async def search_author(self, event: AstrMessageEvent):
        parts = event.message_str.strip().split()
        if len(parts) < 3:
            return event.plain_result("格式: /jm作者 [作者名] [序号]")
        
        *author_parts, order = parts[1:]
        try:
            order = int(order)
            if order < 1:
                return event.plain_result("序号必须≥1")
        except:
            return event.plain_result("序号必须是数字")
        
        client = await self._get_client()
        search_query = f':{" ".join(author_parts)}'
        all_results = []
        author_name = " ".join(author_parts)
        
        try:
            first_page = client.search_site(
                search_query=search_query,
                page=1,
                order_by=JmMagicConstants.ORDER_BY_LATEST
            )
            total_count = first_page.total
            page_size = len(first_page.content)
            all_results.extend(list(first_page.iter_id_title()))
            
            # 计算需要请求的总页数
            if total_count > 0 and page_size > 0:
                total_page = (total_count + page_size - 1) // page_size
                # 请求剩余页
                for page in range(2, total_page + 1):
                    page_result = client.search_site(
                        search_query=search_query,
                        page=page,
                        order_by=JmMagicConstants.ORDER_BY_LATEST
                    )
                    all_results.extend(list(page_result.iter_id_title()))
                    # 提前终止条件
                    if len(all_results) >= order:
                        break

            if len(all_results) < order:
                return event.plain_result(f"作者 {author_name} 共有 {total_count} 部作品\n当前仅获取到 {len(all_results)} 部")
            
            album_id, _ = all_results[order-1]
            album = client.get_album_detail(album_id)
            
            cover_path = self._get_cover_path(album_id)
            if not os.path.exists(cover_path):
                success, result = await self._download_cover(album_id)
                if not success:
                    message = (
                        f"⚠️ 封面下载失败"
                    )
                    return event.plain_result(message)
                cover_path = result
            
            message = (
                f"🎨 JM里共有作者 {author_name} {total_count} 部作品\n"
                f"📖: {album.title}\n"
                f"🆔: {album_id}\n"
                f"🏷️: {', '.join(album.tags[:3])}\n"
                f"📅: {getattr(album, 'pub_date', '未知')}\n"
                f"📃: {self._get_total_pages(client, album)}"
            )
            
            return event.chain_result([
                Plain(text=message),
                Image.fromFileSystem(cover_path)
            ])
        except Exception as e:
            return event.plain_result(f"搜索失败: {str(e)}")

    @filter.command("jm_help")
    async def show_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = (
            "📚命令列表：\n"
            "1️⃣/jm [ID]\n"
            "2️⃣/jm下载 [ID]\n"
            "3️⃣/jm作者 [作者] [序号]\n"
            "4️⃣/jm搜索 [关键词] [序号]\n"
            "5️⃣/jm推荐\n"
            "📌说明：\n"
            "1️⃣根据ID查询(1空格)\n"
            "2️⃣根据ID下载(1空格)\n"
            "3️⃣检索[作者]的本子，返回第[次序](时间降序)本本子(2空格)\n"
            "4️⃣检索含[关键词]的本子，返回第[次序]本本子(2空格)\n"
            "5️⃣从月排行随机推荐"
        )
        yield event.plain_result(help_text)