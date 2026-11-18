import os
import json
import urllib.request
import io
from PIL import Image, ImageDraw

ORG_NAME = "ZoexLab"
DEFAULT_MEMBERS = ["Raxytw", "LuoyiDev"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUTPUT_PNG_PATH = os.path.join(ROOT_DIR, "assets", "all-members.png")

def make_request(url, token=None):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/vnd.github.v3+json"
    }
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"API notice ({url}): {e}")
        return None

def get_org_member_logins(token=None):
    """自動取得組織成員名單，不需手動維護 json"""
    url = f"https://api.github.com/orgs/{ORG_NAME}/members?per_page=100"
    members = make_request(url, token)
    if not members:
        url_public = f"https://api.github.com/orgs/{ORG_NAME}/public_members?per_page=100"
        members = make_request(url_public, token)

    if members:
        return [m["login"] for m in members]
    
    print(f"提示：GitHub API 目前取得組織成員為空（成員可至 https://github.com/orgs/{ORG_NAME}/people 將狀態設為 Public）。")
    print(f"回退使用組織核心名單：{DEFAULT_MEMBERS}")
    return DEFAULT_MEMBERS

def fetch_avatar_image(username):
    """下載成員最新頭像"""
    url = f"https://github.com/{username}.png?size=300"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return Image.open(io.BytesIO(resp.read())).convert("RGBA")
    except Exception as e:
        print(f"無法載入 {username} 的頭像: {e}")
        # 回退建立透明占位圖
        return Image.new("RGBA", (300, 300), (50, 50, 50, 255))

def create_circular_avatar(img, diameter=120, border_width=3, border_color=(88, 166, 255, 230)):
    """裁切超平滑圓形頭像（4x 超採樣抗鋸齒）"""
    scale = 4
    high_res_size = diameter * scale
    
    # 平滑縮放至超採樣尺寸
    resized_img = img.resize((high_res_size, high_res_size), Image.Resampling.LANCZOS)
    
    # 建立圓形遮罩
    mask = Image.new("L", (high_res_size, high_res_size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, high_res_size, high_res_size), fill=255)
    
    # 套用遮罩
    circle_img = Image.new("RGBA", (high_res_size, high_res_size), (0, 0, 0, 0))
    circle_img.paste(resized_img, (0, 0), mask=mask)
    
    # 繪製平滑圓形邊框
    if border_width > 0:
        draw_border = ImageDraw.Draw(circle_img)
        bw = border_width * scale
        draw_border.ellipse(
            (bw // 2, bw // 2, high_res_size - bw // 2, high_res_size - bw // 2),
            outline=border_color,
            width=bw
        )
    
    # 縮小回目標尺寸
    return circle_img.resize((diameter, diameter), Image.Resampling.LANCZOS)

def generate_members_png(member_logins, output_path):
    """將所有組織成員頭像拼合成一張透明背景的 all-members.png"""
    avatar_diameter = 80  # 高畫質圓形尺寸
    gap = 24               # 頭像之間的間距
    padding = 6            # 邊距
    
    count = len(member_logins)
    total_w = padding * 2 + count * avatar_diameter + (count - 1) * gap
    total_h = padding * 2 + avatar_diameter
    
    # 建立透明畫布
    canvas = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    
    # 邊框配色清單（循環使用，呈現精緻多色環）
    border_colors = [
        (255, 121, 198, 240), # 粉紅
        (139, 233, 253, 240), # 藍綠
        (189, 147, 249, 240), # 紫色
        (80, 250, 123, 240)   # 綠色
    ]
    
    for idx, uname in enumerate(member_logins):
        print(f"正在處理成員頭像 [{idx+1}/{count}]: {uname}")
        raw_avatar = fetch_avatar_image(uname)
        border_col = border_colors[idx % len(border_colors)]
        circular_avatar = create_circular_avatar(raw_avatar, diameter=avatar_diameter, border_width=3, border_color=border_col)
        
        x = padding + idx * (avatar_diameter + gap)
        y = padding
        canvas.paste(circular_avatar, (x, y), mask=circular_avatar)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    print(f"成功儲存成員圖片至: {output_path} (尺寸: {total_w}x{total_h})")

def main():
    token = os.environ.get("ORG_TOKEN") or os.environ.get("GITHUB_TOKEN")
    print(f"正在自動抓取 [{ORG_NAME}] 組織成員...")
    logins = get_org_member_logins(token)
    print(f"成員名單: {logins}")
    generate_members_png(logins, OUTPUT_PNG_PATH)

if __name__ == "__main__":
    main()
