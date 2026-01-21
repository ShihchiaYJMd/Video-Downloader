import time
import json
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import yt_dlp

def get_driver():
    """初始化浏览器 (无头模式版)"""
    chrome_options = Options()
    
    # 启用新版无头模式
    chrome_options.add_argument("--headless=new")
    
    # 开启性能日志 (用于抓包)
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    # 静音 & 基础配置
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 无头模式下必须设置大窗口，否则可能点击失败
    driver.set_window_size(1920, 1080)
    
    return driver

def get_video_page_urls(driver, channel_url):
    """抓取频道页面的所有视频链接"""
    print(f"正在访问频道主页: {channel_url}")
    try:
        driver.get(channel_url)
        time.sleep(5) 
        
        video_links = []
        seen_urls = set()
        
        print("正在扫描页面所有链接...")
        elements = driver.find_elements(By.TAG_NAME, 'a')
        
        for elem in elements:
            try:
                href = elem.get_attribute('href')
                text = elem.text.strip()
                
                # 筛选逻辑：包含 /media/ 且有效
                if href and '/media/' in href and 'category' not in href and text:
                    clean_href = href.split('#')[0]
                    # 排除无效标题 (如时间戳 10:20 或纯数字)
                    if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', text) or text.isdigit() or len(text) < 2:
                        continue
                    if clean_href not in seen_urls:
                        video_links.append({'title': text, 'url': clean_href})
                        seen_urls.add(clean_href)
            except:
                continue

        print(f"共找到 {len(video_links)} 个有效视频链接。")
        return video_links
    except Exception as e:
        print(f"访问主页失败: {e}")
        return []

def trigger_playback(driver):
    """模拟点击播放 (支持无头模式下的点击)"""
    selectors = [
        ".largePlayBtn", ".mwEmbedPlayer", "#kplayer_ifp_driver", 
        "button[title='Play']", ".play-button"
    ]
    clicked = False
    for selector in selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, selector)
            if btn.is_displayed():
                ActionChains(driver).move_to_element(btn).click().perform()
                clicked = True
                break
        except:
            pass
    
    if not clicked:
        try:
            # 兜底：点击屏幕中间位置
            body = driver.find_element(By.TAG_NAME, "body")
            ActionChains(driver).move_to_element_with_offset(body, 0, -50).click().perform()
        except:
            pass

def sniff_all_video_urls(driver, page_url):
    """
    智能抓取：返回捕捉到的【所有】潜在 m3u8 链接列表
    """
    print(f"正在分析: {page_url}")
    driver.get(page_url)
    time.sleep(8)  # 增加页面加载时间，确保页面完全加载
    
    # 清除旧日志
    driver.get_log('performance')
    
    # 触发播放
    trigger_playback(driver)
    time.sleep(3)  # 播放触发后等待，让视频加载
    
    print("  -> [监控] 正在监听网络请求...")
    
    found_candidates = []
    
    # 初始等待 45 秒，增加捕获时间
    stop_listening_time = time.time() + 45 
    
    # 记录上一次发现链接的时间，用于判断是否需要继续等待
    last_found_time = time.time()
    
    while time.time() < stop_listening_time:
        logs = driver.get_log('performance')
        
        for entry in logs:
            try:
                message = json.loads(entry['message'])['message']
                if message['method'] == 'Network.requestWillBeSent':
                    request_url = message['params']['request']['url']
                    
                    # 放宽匹配条件，捕获更多可能的流地址
                    if ('index.m3u8' in request_url or '.m3u8' in request_url) and \
                       ('Policy=' in request_url or 'Signature=' in request_url or 'm3u8' in request_url):
                        
                        # 排除分片请求，只抓主索引
                        if 'seg-' in request_url or 'segment' in request_url:
                            continue
                        
                        if request_url not in found_candidates:
                            found_candidates.append(request_url)
                            print(f"  -> [捕获] 发现第 {len(found_candidates)} 个流地址: {request_url[-100:]}")
                            
                            # 发现新链接后延长监听时间
                            stop_listening_time = time.time() + 15
                            last_found_time = time.time()
                            
            except Exception as e:
                pass
        
        # 检查是否有新发现，如果没有新发现超过8秒则可能已捕获全部
        if time.time() - last_found_time > 8 and len(found_candidates) > 0:
            print(f"  -> [监控] 已连续8秒未发现新流地址，当前已捕获 {len(found_candidates)} 个")
            # 不立即退出，继续等待一段时间以确保捕获所有流
            if time.time() - last_found_time > 15:
                print(f"  -> [完成] 确认无更多流地址，总共捕获 {len(found_candidates)} 个")
                break
        
        time.sleep(0.5)  # 减少等待间隔，提高响应速度
        
    print(f"  -> [完成] 总共捕获 {len(found_candidates)} 个流地址")
    return found_candidates

def download_video(url, title, save_path, suffix=""):
    """
    下载视频
    :param save_path: 用户指定的保存文件夹路径
    :param suffix: 文件名后缀，用于多视角区分
    """
    # 确保保存目录存在
    if not os.path.exists(save_path):
        try:
            os.makedirs(save_path)
            print(f"  -> [创建目录] {save_path}")
        except Exception as e:
            print(f"  -> [错误] 无法创建目录: {e}")
            return

    # 清理文件名
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
    if len(safe_title) > 80:
        safe_title = safe_title[:80]
    
    final_filename = f"{safe_title}{suffix}"
    output_path = os.path.join(save_path, final_filename)
    
    if os.path.exists(f"{output_path}.mp4"):
        print(f"  -> [跳过] 文件已存在: {final_filename}.mp4")
        return

    print(f"  -> 开始下载: {final_filename}")
    
    ydl_opts = {
        'outtmpl': f'{output_path}.%(ext)s',
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'hls_prefer_native': True,
        'concurrent_fragment_downloads': 4,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"  -> [成功] 下载完成: {final_filename}.mp4\n")
    except Exception as e:
        print(f"  -> [失败] 下载出错: {e}\n")

def main():
    print("=== Selenium 智能视频爬虫 (支持多视角/自定义路径) ===")
    
    # 1. 输入 URL
    channel_url = input("1. 请输入频道主页 URL: ").strip()
    if not channel_url:
        print("URL 不能为空！")
        return

    # 2. 输入 m (过滤参数)
    m_input = input("2. 请输入要下载每个页面的【最后 m 个】视频 (回车默认 m=1): ").strip()
    if m_input.isdigit():
        m = int(m_input)
        if m <= 0: m = 1
    else:
        m = 1
    
    # 3. 输入保存路径
    default_path = "./video"
    path_input = input(f"3. 请输入视频保存路径 (回车默认 {default_path}): ").strip()
    
    if not path_input:
        save_path = default_path
    else:
        # 统一路径分隔符，防止 windows/linux 混用问题
        save_path = path_input.replace("\\", "/")

    print(f"\n[配置确认]\n- 目标: {channel_url}\n- 模式: 下载最后 {m} 个流\n- 保存: {save_path}\n")

    driver = get_driver()
    try:
        videos = get_video_page_urls(driver, channel_url)
        
        if not videos:
            print("未找到视频链接，程序结束。")
            return

        print(f"\n开始处理 {len(videos)} 个视频页 (后台模式)...\n")
        
        for i, video in enumerate(videos):
            print(f"--- 进度 {i+1}/{len(videos)}: {video['title']} ---")
            
            # 在处理第一个视频前，添加额外的等待和刷新，确保浏览器状态正常
            if i == 0:
                print("  -> [初始化] 处理第一个视频，刷新页面并等待...")
                driver.refresh()
                time.sleep(3)
            
            # 获取所有链接
            all_candidates = sniff_all_video_urls(driver, video['url'])
            
            if not all_candidates:
                print(f"  -> [超时] 未能捕获任何 m3u8 链接。")
                continue
            
            # 筛选最后 m 个
            target_urls = all_candidates[-m:]
            
            print(f"  -> [筛选] 捕获 {len(all_candidates)} 个流，下载最后 {len(target_urls)} 个。")
            
            for idx, m3u8_url in enumerate(target_urls):
                suffix = ""
                # 如果只有1个，不需要后缀；如果有多个，加 _view_X
                if len(target_urls) > 1:
                    suffix = f"_view_{idx + 1}"
                
                # 传入 save_path
                download_video(m3u8_url, video['title'], save_path, suffix)
            
            time.sleep(2)
            
    finally:
        driver.quit()
        print(f"\n所有任务已完成。视频保存在: {save_path}")

if __name__ == "__main__":
    main()