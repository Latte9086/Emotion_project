import os
import pptx
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Premium Dark Theme Palette (Matching slides.html & slides.pdf)
    c_bg = RGBColor(9, 13, 24)              # #090d18 (deep dark background)
    c_header_bg = RGBColor(15, 23, 42)      # #0f172a (dark navy header)
    c_card_bg = RGBColor(20, 29, 49)        # #141d31 (glassmorphic dark card)
    c_card_border = RGBColor(38, 53, 79)    # #26354f (card border)
    c_code_bg = RGBColor(7, 11, 20)         # #070b14 (code block background)
    c_code_border = RGBColor(30, 58, 102)   # #1e3a66 (code border)
    c_code_text = RGBColor(147, 197, 253)   # #93c5fd (syntax cyan-blue)

    c_blue = RGBColor(37, 99, 235)          # #2563eb
    c_cyan = RGBColor(56, 189, 248)         # #38bdf8
    c_emerald = RGBColor(16, 185, 129)      # #10b981
    c_amber = RGBColor(245, 158, 11)        # #f59e0b
    c_purple = RGBColor(168, 85, 247)       # #a855f7

    c_text_white = RGBColor(255, 255, 255)  # #ffffff
    c_text_light = RGBColor(203, 213, 225)  # #cbd5e1
    c_text_muted = RGBColor(148, 163, 184)  # #94a3b8

    def set_slide_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = c_bg
        bg.line.fill.background()

    def add_header(slide, badge_text, title_text, subtitle_text, badge_color=c_blue, slide_num=None):
        # Header background banner
        banner = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.15))
        banner.fill.solid()
        banner.fill.fore_color.rgb = c_header_bg
        banner.line.fill.background()

        # Bottom accent divider line on header
        div = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(1.15), Inches(13.333), Inches(0.02))
        div.fill.solid()
        div.fill.fore_color.rgb = c_card_border
        div.line.fill.background()

        # Badge pill
        badge_w = max(1.8, len(badge_text) * 0.14)
        badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.2), Inches(badge_w), Inches(0.32))
        badge.fill.solid()
        badge.fill.fore_color.rgb = badge_color
        badge.line.fill.background()
        tf_b = badge.text_frame
        tf_b.word_wrap = True
        p_b = tf_b.paragraphs[0]
        p_b.text = badge_text
        p_b.font.size = Pt(10.5)
        p_b.font.bold = True
        p_b.font.color.rgb = c_text_white
        p_b.alignment = PP_ALIGN.CENTER

        # Title
        tx_box = slide.shapes.add_textbox(Inches(0.8 + badge_w + 0.3), Inches(0.12), Inches(10.5 - badge_w), Inches(0.5))
        tf = tx_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(19)
        p.font.bold = True
        p.font.color.rgb = c_text_white

        # Subtitle
        tx_sub = slide.shapes.add_textbox(Inches(0.8 + badge_w + 0.3), Inches(0.62), Inches(10.5 - badge_w), Inches(0.4))
        tf_sub = tx_sub.text_frame
        p_sub = tf_sub.paragraphs[0]
        p_sub.text = subtitle_text
        p_sub.font.size = Pt(11.5)
        p_sub.font.color.rgb = c_cyan

        # Slide Number (top right)
        if slide_num:
            num_box = slide.shapes.add_textbox(Inches(11.5), Inches(0.25), Inches(1.2), Inches(0.4))
            tf_n = num_box.text_frame
            p_n = tf_n.paragraphs[0]
            p_n.text = f"{slide_num:02d} / 10"
            p_n.font.size = Pt(11)
            p_n.font.color.rgb = c_text_muted
            p_n.font.name = "Consolas"
            p_n.alignment = PP_ALIGN.RIGHT

        # Bottom footer line
        footer_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(7.1), Inches(13.333), Inches(0.02))
        footer_line.fill.solid()
        footer_line.fill.fore_color.rgb = c_card_border
        footer_line.line.fill.background()

        # Footer text
        ft_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.12), Inches(11.7), Inches(0.35))
        tf_ft = ft_box.text_frame
        p_ft = tf_ft.paragraphs[0]
        p_ft.text = "情動イメージング演習 進捗報告 | 情報・データサイエンス学部3年 | 実装進捗：Day1〜Day3課題完了"
        p_ft.font.size = Pt(9.5)
        p_ft.font.color.rgb = c_text_muted

    # ==========================================
    # SLIDE 1: Cover Slide
    # ==========================================
    slide1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide1)

    # Outer decorative glow container
    card_deco = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.0), Inches(11.333), Inches(5.5))
    card_deco.fill.solid()
    card_deco.fill.fore_color.rgb = c_card_bg
    card_deco.line.color.rgb = c_card_border

    # Top accent bar on card
    top_bar = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.0), Inches(11.333), Inches(0.12))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = c_cyan
    top_bar.line.fill.background()

    badge1 = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.6), Inches(1.5), Inches(3.8), Inches(0.42))
    badge1.fill.solid()
    badge1.fill.fore_color.rgb = c_blue
    badge1.line.fill.background()
    p1_b = badge1.text_frame.paragraphs[0]
    p1_b.text = "情動イメージング演習 進捗報告"
    p1_b.font.size = Pt(12)
    p1_b.font.bold = True
    p1_b.font.color.rgb = c_text_white
    p1_b.alignment = PP_ALIGN.CENTER

    tb1 = slide1.shapes.add_textbox(Inches(1.6), Inches(2.1), Inches(10.1), Inches(1.8))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p1_1 = tf1.paragraphs[0]
    p1_1.text = "OpenFaceを用いた顔画像からの情動解析"
    p1_1.font.size = Pt(34)
    p1_1.font.bold = True
    p1_1.font.color.rgb = c_text_white

    p1_2 = tf1.add_paragraph()
    p1_2.text = "〜 第1回〜第3回演習課題の実装完了と独自発展システムの開発報告 〜"
    p1_2.font.size = Pt(19)
    p1_2.font.color.rgb = c_cyan

    tb1_info = slide1.shapes.add_textbox(Inches(1.6), Inches(4.1), Inches(10.1), Inches(2.0))
    tf1_info = tb1_info.text_frame
    tf1_info.word_wrap = True
    
    p1_desc = tf1_info.paragraphs[0]
    p1_desc.text = "■ 実施状況サマリー:\n• 実活動日（Day1・Day2）においてテキスト全3回分の課題をすべて前倒し実装完了\n• 頭部姿勢(Head Pose)・Action Unit・時系列差分・平滑化・Emotion Timelineの実装\n• OpenCVとMatplotlibを同期させたリアルタイム動画・情動可視化ツールの独自開発"
    p1_desc.font.size = Pt(12.5)
    p1_desc.font.color.rgb = c_text_light

    p1_foot = tf1_info.add_paragraph()
    p1_foot.text = "\n発表日: 2026年10月22日 | 情報・データサイエンス学部 3年"
    p1_foot.font.size = Pt(12)
    p1_foot.font.color.rgb = c_text_muted

    # ==========================================
    # SLIDE 2: Overall Progress Summary
    # ==========================================
    slide2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide2)
    add_header(slide2, "PROGRESS SUMMARY", "演習全体の進捗状況サマリー", "シラバス全4回に対する我々の実作業（Day 1・Day 2）での前倒し達成対比", c_emerald, 2)

    stages = [
        ("第1回 相当 (Day1実施)", "顔を「データ」として測る", c_blue, [
            "OpenFaceによる動画からのデータ抽出",
            "頭部姿勢 (Pitch/Yaw/Roll) の解析",
            "頭部姿勢時系列グラフ化 (plot_sayu.py)",
            "【達成】動画動作と数値の対応関係を把握"
        ]),
        ("第2回 相当 (Day1実施)", "表情を数値として測る", c_blue, [
            "Facial Action Unit (AU) の時系列抽出",
            "笑顔(AU06, AU12)・驚き(AU01,02,05,25,26)",
            "独自情動指標の作成 (2-kadai.py)",
            "【達成】Happy, Surprise, Sadness を数式化"
        ]),
        ("第3回 相当 (Day2実施)", "時間変化から情動を読む", c_emerald, [
            "AU12のフレーム差分計算 (3-1.py)",
            "しきい値判定によるイベント検出 (3-2.py)",
            "移動平均によるノイズ平滑化 (3-2_MA.py)",
            "4段 Emotion Timeline の作成 (3-hukusen.py)",
            "【独自発展】動画同期プレイヤー (3-WB.py)"
        ])
    ]

    for i, (tag, title, col, items) in enumerate(stages):
        x = Inches(0.8 + i * 3.95)
        card = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.45), Inches(3.75), Inches(5.3))
        card.fill.solid()
        card.fill.fore_color.rgb = c_card_bg
        card.line.color.rgb = c_card_border

        # Top accent bar
        bar = slide2.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, Inches(1.45), Inches(3.75), Inches(0.12))
        bar.fill.solid()
        bar.fill.fore_color.rgb = col
        bar.line.fill.background()

        tb = slide2.shapes.add_textbox(x + Inches(0.2), Inches(1.7), Inches(3.35), Inches(4.8))
        tf = tb.text_frame
        tf.word_wrap = True

        p_t = tf.paragraphs[0]
        p_t.text = tag
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = col

        p_sub = tf.add_paragraph()
        p_sub.text = title + "\n"
        p_sub.font.size = Pt(15)
        p_sub.font.bold = True
        p_sub.font.color.rgb = c_text_white

        for item in items:
            p_item = tf.add_paragraph()
            p_item.text = "• " + item
            p_item.font.size = Pt(11)
            p_item.font.color.rgb = c_cyan if "【" in item else c_text_light
            p_item.font.bold = "【" in item

    # ==========================================
    # SLIDE 3: Day 1 - Head Pose (Sayu.csv)
    # ==========================================
    slide3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide3)
    add_header(slide3, "DAY 1 実績 (1)", "頭部姿勢の時系列可視化 (Head Pose)", "動画中の頭部運動（左右・上下・傾き）を客観的な角度（rad）データとして抽出", c_blue, 3)

    c_left3 = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4))
    c_left3.fill.solid()
    c_left3.fill.fore_color.rgb = c_card_bg
    c_left3.line.color.rgb = c_card_border

    tb3 = slide3.shapes.add_textbox(Inches(1.0), Inches(1.55), Inches(5.2), Inches(5.1))
    tf3 = tb3.text_frame
    tf3.word_wrap = True

    p = tf3.paragraphs[0]
    p.text = "■ 実施内容・目的"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = c_cyan

    p = tf3.add_paragraph()
    p.text = "• 対象データ: Sayu.csv (頭部運動動画の解析結果)\n• pose_Rx (Pitch: 上下), pose_Ry (Yaw: 左右), pose_Rz (Roll: 傾き) の3軸角度変化を抽出・プロット。\n• 「動画を目視する」状態から「数値変化として比較・統計処理できる」データへの変換を実証。"
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_light

    p = tf3.add_paragraph()
    p.text = "\n■ 作成コード (plot_sayu.py 抜粋)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = c_cyan

    # Code Box shape
    code_box3 = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(3.6), Inches(5.2), Inches(1.7))
    code_box3.fill.solid()
    code_box3.fill.fore_color.rgb = c_code_bg
    code_box3.line.color.rgb = c_code_border
    tf_c3 = code_box3.text_frame
    tf_c3.word_wrap = True
    p_c3 = tf_c3.paragraphs[0]
    p_c3.text = "df = pd.read_csv('Sayu.csv')\ndf.columns = df.columns.str.strip()\nplt.plot(df['timestamp'], df['pose_Rx'], label='Pitch')\nplt.plot(df['timestamp'], df['pose_Ry'], label='Yaw')\nplt.plot(df['timestamp'], df['pose_Rz'], label='Roll')\nplt.savefig('Sayu_pose.png')"
    p_c3.font.size = Pt(10)
    p_c3.font.name = "Consolas"
    p_c3.font.color.rgb = c_code_text

    tb3_post = slide3.shapes.add_textbox(Inches(1.0), Inches(5.4), Inches(5.2), Inches(1.3))
    tf3_post = tb3_post.text_frame
    p = tf3_post.paragraphs[0]
    p.text = "■ 考察・知見\n・左右に振ったタイミングで pose_Ry が大きく正負に変動。\n・身体動作を明瞭な時系列ピークとして捉えることが確認できた。"
    p.font.size = Pt(11)
    p.font.color.rgb = c_text_muted

    # Right Card: Image container
    c_right3 = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.4))
    c_right3.fill.solid()
    c_right3.fill.fore_color.rgb = c_card_bg
    c_right3.line.color.rgb = c_card_border

    img_path3 = "images/Sayu_pose.png"
    if os.path.exists(img_path3):
        slide3.shapes.add_picture(img_path3, Inches(7.0), Inches(1.8), width=Inches(5.3))

    tb3_cap = slide3.shapes.add_textbox(Inches(7.0), Inches(6.2), Inches(5.3), Inches(0.4))
    tf3_cap = tb3_cap.text_frame
    p = tf3_cap.paragraphs[0]
    p.text = "図: Sayu_pose.png (頭部3軸回転角の時系列プロット)"
    p.font.size = Pt(10)
    p.font.color.rgb = c_text_muted
    p.font.name = "Consolas"
    p.alignment = PP_ALIGN.CENTER

    # ==========================================
    # SLIDE 4: Day 1 - Action Unit (2-2.py)
    # ==========================================
    slide4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide4)
    add_header(slide4, "DAY 1 実績 (2)", "Action Unit (AU) による顔表情の数値化", "FACS（顔面動作符号化システム）に基づき、筋肉の微小動作を強度値として定量化", c_blue, 4)

    c_left4 = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(6.0), Inches(5.4))
    c_left4.fill.solid()
    c_left4.fill.fore_color.rgb = c_card_bg
    c_left4.line.color.rgb = c_card_border

    tb4 = slide4.shapes.add_textbox(Inches(1.0), Inches(1.55), Inches(5.6), Inches(5.1))
    tf4 = tb4.text_frame
    tf4.word_wrap = True

    p = tf4.paragraphs[0]
    p.text = "■ 観測対象と筋運動の対応"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = c_cyan

    p = tf4.add_paragraph()
    p.text = "• AU06_r (頬上げ): 眼輪筋の収縮。自然な笑顔で強く生起。\n• AU12_r (口角上げ): 大頬骨筋の収縮。笑顔の主要決定因子。\n• AU04_r (眉下げ): 皺眉筋の収縮。困惑・集中・不快時に上昇。"
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_light

    p = tf4.add_paragraph()
    p.text = "\n■ 作成コード (2-2.py)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = c_cyan

    # Code Box
    code_box4 = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(3.6), Inches(5.6), Inches(1.7))
    code_box4.fill.solid()
    code_box4.fill.fore_color.rgb = c_code_bg
    code_box4.line.color.rgb = c_code_border
    tf_c4 = code_box4.text_frame
    tf_c4.word_wrap = True
    p_c4 = tf_c4.paragraphs[0]
    p_c4.text = "df = pd.read_csv('2-2.csv')\ndf.columns = df.columns.str.strip()\nplt.plot(df['timestamp'], df['AU06_r'], label='AU06')\nplt.plot(df['timestamp'], df['AU12_r'], label='AU12')\nplt.plot(df['timestamp'], df['AU04_r'], label='AU04')\nplt.legend(); plt.show()"
    p_c4.font.size = Pt(10)
    p_c4.font.name = "Consolas"
    p_c4.font.color.rgb = c_code_text

    tb4_post = slide4.shapes.add_textbox(Inches(1.0), Inches(5.4), Inches(5.6), Inches(1.3))
    tf4_post = tb4_post.text_frame
    p = tf4_post.paragraphs[0]
    p.text = "■ 観測結果と考察\n・笑顔区間（中盤）において、AU06とAU12が同期して急上昇。\n・感情を主観で決めるのではなく、筋運動の客観強度として評価可能。"
    p.font.size = Pt(11)
    p.font.color.rgb = c_text_muted

    # Right Card: Image
    c_right4 = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.2), Inches(1.4), Inches(5.3), Inches(5.4))
    c_right4.fill.solid()
    c_right4.fill.fore_color.rgb = c_card_bg
    c_right4.line.color.rgb = c_card_border

    img_path4 = "images/2-2.png"
    if os.path.exists(img_path4):
        slide4.shapes.add_picture(img_path4, Inches(8.0), Inches(1.6), height=Inches(4.8))

    tb4_cap = slide4.shapes.add_textbox(Inches(7.2), Inches(6.45), Inches(5.3), Inches(0.35))
    tf4_cap = tb4_cap.text_frame
    p = tf4_cap.paragraphs[0]
    p.text = "図: 2-2.png (AU06, AU12, AU04 の時系列変化)"
    p.font.size = Pt(10)
    p.font.color.rgb = c_text_muted
    p.font.name = "Consolas"
    p.alignment = PP_ALIGN.CENTER

    # ==========================================
    # SLIDE 5: Day 1 - Surprise & Custom Emotion Index (2-3.py & 2-kadai.py)
    # ==========================================
    slide5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide5)
    add_header(slide5, "DAY 1 実績 (3)", "複合AU分析と独自情動指標のモデリング", "複数AUの組み合わせによる「驚き(Surprise)」分析と独自指標（Happy, Sadness等）の設計", c_blue, 5)

    c_l5 = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4))
    c_l5.fill.solid()
    c_l5.fill.fore_color.rgb = c_card_bg
    c_l5.line.color.rgb = c_card_border

    tb_l5 = slide5.shapes.add_textbox(Inches(1.0), Inches(1.55), Inches(5.2), Inches(1.3))
    tf_l5 = tb_l5.text_frame
    tf_l5.word_wrap = True
    p = tf_l5.paragraphs[0]
    p.text = "演習3: 驚き(Surprise)区間のAU多変量解析 (2-3.py)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = c_cyan
    p = tf_l5.add_paragraph()
    p.text = "• 内外眉上げ(AU01,02)、上まぶた(AU05)、開口(AU25,26)が同時に生起する瞬間を可視化。"
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_light

    img_path5_1 = "images/2-3.png"
    if os.path.exists(img_path5_1):
        slide5.shapes.add_picture(img_path5_1, Inches(1.2), Inches(3.0), width=Inches(4.8))

    c_r5 = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.4))
    c_r5.fill.solid()
    c_r5.fill.fore_color.rgb = c_card_bg
    c_r5.line.color.rgb = c_card_border

    tb_r5 = slide5.shapes.add_textbox(Inches(7.0), Inches(1.55), Inches(5.3), Inches(1.4))
    tf_r5 = tb_r5.text_frame
    tf_r5.word_wrap = True
    p = tf_r5.paragraphs[0]
    p.text = "課題: 独自 Emotion Index の数式定義 (2-kadai.py)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = c_cyan
    p = tf_r5.add_paragraph()
    p.text = "df['happy'] = df['AU25_r']\ndf['surprise'] = df['AU01_r'] + df['AU02_r'] + df['AU05_r'] + df['AU26_r']\ndf['sadness'] = df['AU04_r']"
    p.font.size = Pt(10)
    p.font.name = "Consolas"
    p.font.color.rgb = c_code_text

    img_path5_2 = "images/2-kadai.png"
    if os.path.exists(img_path5_2):
        slide5.shapes.add_picture(img_path5_2, Inches(7.0), Inches(3.3), width=Inches(5.3))

    # ==========================================
    # SLIDE 6: Day 2 - Time-series Diff & Event Detection
    # ==========================================
    slide6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide6)
    add_header(slide6, "DAY 2 実績 (1)", "時系列差分とイベント検出フラグ化", "静止画的特徴から動画時系列へ：急峻な変化点の抽出としきい値による離散イベント化", c_blue, 6)

    c_l6 = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4))
    c_l6.fill.solid()
    c_l6.fill.fore_color.rgb = c_card_bg
    c_l6.line.color.rgb = c_card_border

    tb_l6 = slide6.shapes.add_textbox(Inches(1.0), Inches(1.55), Inches(5.2), Inches(1.4))
    tf_l6 = tb_l6.text_frame
    tf_l6.word_wrap = True
    p = tf_l6.paragraphs[0]
    p.text = "① フレーム間差分による変化点検出 (3-1.py)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = c_cyan
    p = tf_l6.add_paragraph()
    p.text = "• コード: df['AU12_diff'] = df['AU12_r'].diff()\n• 表情の「絶対値」だけでなく「表情が動いた瞬間」を特定。"
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_light

    img_path6_1 = "images/3-1.png"
    if os.path.exists(img_path6_1):
        slide6.shapes.add_picture(img_path6_1, Inches(1.2), Inches(3.1), width=Inches(4.8))

    c_r6 = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.4))
    c_r6.fill.solid()
    c_r6.fill.fore_color.rgb = c_card_bg
    c_r6.line.color.rgb = c_card_border

    tb_r6 = slide6.shapes.add_textbox(Inches(7.0), Inches(1.55), Inches(5.3), Inches(1.4))
    tf_r6 = tb_r6.text_frame
    tf_r6.word_wrap = True
    p = tf_r6.paragraphs[0]
    p.text = "② 閾値処理によるイベントフラグ化 (3-2.py)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = c_cyan
    p = tf_r6.add_paragraph()
    p.text = "• コード: df['smileFlag'] = (df['AU12_r'] > 2).astype(int)\n• 連続値を0/1のイベント生起系列としてバイナリ化。"
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_light

    img_path6_2 = "images/3-2.png"
    if os.path.exists(img_path6_2):
        slide6.shapes.add_picture(img_path6_2, Inches(7.0), Inches(3.2), width=Inches(5.3))

    # ==========================================
    # SLIDE 7: Day 2 - Moving Average (3-2_MA.py)
    # ==========================================
    slide7 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide7)
    add_header(slide7, "DAY 2 実績 (2)", "移動平均フィルタによるノイズ低減と平滑化", "顔画像トラッキング特有の高周波ノイズを除去し、本質的な情動トレンドを抽出", c_blue, 7)

    c_left7 = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4))
    c_left7.fill.solid()
    c_left7.fill.fore_color.rgb = c_card_bg
    c_left7.line.color.rgb = c_card_border

    tb7 = slide7.shapes.add_textbox(Inches(1.0), Inches(1.55), Inches(5.2), Inches(5.1))
    tf7 = tb7.text_frame
    tf7.word_wrap = True

    p = tf7.paragraphs[0]
    p.text = "■ 課題意識とアプローチ"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = c_cyan

    p = tf7.add_paragraph()
    p.text = "• OpenFaceの推定値には微小なフレーム間のジッターやノイズが混入しやすい。\n• 移動平均 (Rolling Mean) を適用し、安定した情動軌跡を算出。"
    p.font.size = Pt(11)
    p.font.color.rgb = c_text_light

    p = tf7.add_paragraph()
    p.text = "\n■ 作成コード (3-2_MA.py)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = c_cyan

    # Code Box
    code_box7 = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(3.4), Inches(5.2), Inches(2.0))
    code_box7.fill.solid()
    code_box7.fill.fore_color.rgb = c_code_bg
    code_box7.line.color.rgb = c_code_border
    tf_c7 = code_box7.text_frame
    tf_c7.word_wrap = True
    p_c7 = tf_c7.paragraphs[0]
    p_c7.text = "df['AU_smooth'] = (\n    df['AU12_r']\n    .rolling(window=8, center=True)\n    .mean()\n)\nplt.plot(df['timestamp'], df['AU12_r'], label='Raw')\nplt.plot(df['timestamp'], df['AU_smooth'], label='Smooth')"
    p_c7.font.size = Pt(9.5)
    p_c7.font.name = "Consolas"
    p_c7.font.color.rgb = c_code_text

    tb7_post = slide7.shapes.add_textbox(Inches(1.0), Inches(5.5), Inches(5.2), Inches(1.2))
    tf7_post = tb7_post.text_frame
    p = tf7_post.paragraphs[0]
    p.text = "■ 考察：windowサイズのトレードオフ\n・window=8 (約0.25秒分): 立ち上がり遅延を抑えつつ振動を効果的に除去。"
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_muted

    c_right7 = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.4))
    c_right7.fill.solid()
    c_right7.fill.fore_color.rgb = c_card_bg
    c_right7.line.color.rgb = c_card_border

    img_path7 = "images/3-2_MA.png"
    if os.path.exists(img_path7):
        slide7.shapes.add_picture(img_path7, Inches(7.0), Inches(1.8), width=Inches(5.3))

    tb7_cap = slide7.shapes.add_textbox(Inches(6.8), Inches(6.2), Inches(5.7), Inches(0.4))
    tf7_cap = tb7_cap.text_frame
    p = tf7_cap.paragraphs[0]
    p.text = "図: 3-2_MA.png (生データ vs 移動平均平滑化データの比較)"
    p.font.size = Pt(10)
    p.font.color.rgb = c_text_muted
    p.font.name = "Consolas"
    p.alignment = PP_ALIGN.CENTER

    # ==========================================
    # SLIDE 8: Day 2 - Emotion Timeline (3-hukusen.py)
    # ==========================================
    slide8 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide8)
    add_header(slide8, "DAY 2 実績 (3)", "複合時系列可視化（Emotion Timeline）の構築", "テキスト第3コマの最重要課題：複数指標（Smile, AU04, 頭部運動, まばたき）を多段統合", c_emerald, 8)

    c_left8 = slide8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4))
    c_left8.fill.solid()
    c_left8.fill.fore_color.rgb = c_card_bg
    c_left8.line.color.rgb = c_card_border

    tb8 = slide8.shapes.add_textbox(Inches(1.0), Inches(1.55), Inches(5.2), Inches(5.1))
    tf8 = tb8.text_frame
    tf8.word_wrap = True

    p = tf8.paragraphs[0]
    p.text = "■ Emotion Timeline 構成要素"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = c_cyan

    p = tf8.add_paragraph()
    p.text = "1. Smile Score: (AU12_r > 2) → 笑顔イベント\n2. AU04: (AU04_r > 1) → 眉間の緊張・集中\n3. Head movement: (pose_Rz.diff() < -0.005) → 首の傾き\n4. Blink: (AU45_c > 0) → まばたき生起フラグ"
    p.font.size = Pt(11)
    p.font.color.rgb = c_text_light

    p = tf8.add_paragraph()
    p.text = "\n■ 作成コード (3-hukusen.py 抜粋)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = c_cyan

    # Code Box
    code_box8 = slide8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(3.6), Inches(5.2), Inches(1.7))
    code_box8.fill.solid()
    code_box8.fill.fore_color.rgb = c_code_bg
    code_box8.line.color.rgb = c_code_border
    tf_c8 = code_box8.text_frame
    tf_c8.word_wrap = True
    p_c8 = tf_c8.paragraphs[0]
    p_c8.text = "fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)\naxes[0].plot(df['timestamp'], df['Smile Score'])\naxes[1].plot(df['timestamp'], df['AU04'])\naxes[2].plot(df['timestamp'], df['Head movement'])\naxes[3].plot(df['timestamp'], df['Blink'])"
    p_c8.font.size = Pt(9.5)
    p_c8.font.name = "Consolas"
    p_c8.font.color.rgb = c_code_text

    tb8_post = slide8.shapes.add_textbox(Inches(1.0), Inches(5.4), Inches(5.2), Inches(1.3))
    tf8_post = tb8_post.text_frame
    p = tf8_post.paragraphs[0]
    p.text = "■ 成果と意義\n・異種指標の同期により「頷きと同時に笑顔が生じる」「考え込むときにまばたきが減る」等の共起現象を発見可能に。"
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_muted

    c_right8 = slide8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.4))
    c_right8.fill.solid()
    c_right8.fill.fore_color.rgb = c_card_bg
    c_right8.line.color.rgb = c_card_border

    img_path8 = "images/3-hukusen.png"
    if os.path.exists(img_path8):
        slide8.shapes.add_picture(img_path8, Inches(7.5), Inches(1.6), height=Inches(4.8))

    tb8_cap = slide8.shapes.add_textbox(Inches(6.8), Inches(6.45), Inches(5.7), Inches(0.35))
    tf8_cap = tb8_cap.text_frame
    p = tf8_cap.paragraphs[0]
    p.text = "図: 3-hukusen.png (4段マルチプロットによるEmotion Timeline)"
    p.font.size = Pt(10)
    p.font.color.rgb = c_text_muted
    p.font.name = "Consolas"
    p.alignment = PP_ALIGN.CENTER

    # ==========================================
    # SLIDE 9: Advanced Work - Synchronized Player (3-WB.py)
    # ==========================================
    slide9 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide9)
    add_header(slide9, "ADVANCED WORK", "動画・時系列グラフ リアルタイム同期プレイヤー", "テキストの構想をさらに発展：OpenCVとMatplotlibのアニメーションによる完全同期可視化", c_amber, 9)

    c_left9 = slide9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.4))
    c_left9.fill.solid()
    c_left9.fill.fore_color.rgb = c_card_bg
    c_left9.line.color.rgb = c_card_border

    tb9 = slide9.shapes.add_textbox(Inches(1.0), Inches(1.55), Inches(5.2), Inches(5.1))
    tf9 = tb9.text_frame
    tf9.word_wrap = True

    p = tf9.paragraphs[0]
    p.text = "■ 独自開発の狙いと特徴 (3-WB.py)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = c_cyan

    p = tf9.add_paragraph()
    p.text = "• テキスト記載の「上段に動画、中段にAU、下段に頭部運動」という理想構成を静止画ではなく動的同期プレイヤーとして具現化。\n• 技術構成: cv2.VideoCapture + FuncAnimation\n• 再生位置バー（赤破線）が現在のフレーム時刻に追従してリアルタイム移動。"
    p.font.size = Pt(11)
    p.font.color.rgb = c_text_light

    p = tf9.add_paragraph()
    p.text = "\n■ 主要実装ハイライト"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = c_cyan

    # Code Box
    code_box9 = slide9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(3.6), Inches(5.2), Inches(1.7))
    code_box9.fill.solid()
    code_box9.fill.fore_color.rgb = c_code_bg
    code_box9.line.color.rgb = c_code_border
    tf_c9 = code_box9.text_frame
    tf_c9.word_wrap = True
    p_c9 = tf_c9.paragraphs[0]
    p_c9.text = "gs = fig.add_gridspec(3, 1, height_ratios=[2, 1, 1])\ndef update(frame_idx):\n    ret, frame = cap.read()\n    im.set_data(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))\n    line_au.set_xdata([t, t])\n    line_head.set_xdata([t, t])"
    p_c9.font.size = Pt(9.5)
    p_c9.font.name = "Consolas"
    p_c9.font.color.rgb = c_code_text

    tb9_post = slide9.shapes.add_textbox(Inches(1.0), Inches(5.4), Inches(5.2), Inches(1.3))
    tf9_post = tb9_post.text_frame
    p = tf9_post.paragraphs[0]
    p.text = "■ 効果\n・数値ピークと実際の顔の動きを遅延なく直感照合でき、アノテーション検証効率が飛躍的に向上。"
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_muted

    c_right9 = slide9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.4))
    c_right9.fill.solid()
    c_right9.fill.fore_color.rgb = c_card_bg
    c_right9.line.color.rgb = c_card_border

    img_path9 = "images/3-WB.png"
    if os.path.exists(img_path9):
        slide9.shapes.add_picture(img_path9, Inches(7.5), Inches(1.6), height=Inches(4.8))

    tb9_cap = slide9.shapes.add_textbox(Inches(6.8), Inches(6.45), Inches(5.7), Inches(0.35))
    tf9_cap = tb9_cap.text_frame
    p = tf9_cap.paragraphs[0]
    p.text = "図: 3-WB.png (動画フレームとAU・頭部運動の完全同期ビューア)"
    p.font.size = Pt(10)
    p.font.color.rgb = c_text_muted
    p.font.name = "Consolas"
    p.alignment = PP_ALIGN.CENTER

    # ==========================================
    # SLIDE 10: Conclusion & Next Step
    # ==========================================
    slide10 = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide10)
    add_header(slide10, "CONCLUSION & FUTURE WORK", "成果のまとめと第4回（ミニプロジェクト）への展望", "第4回に向けた挑戦：マルチモーダル特徴量による『嘘発見器』の精度向上とアプリ開発", c_emerald, 10)

    # 2 Big Cards
    c10_1 = slide10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.45), Inches(5.6), Inches(5.3))
    c10_1.fill.solid()
    c10_1.fill.fore_color.rgb = c_card_bg
    c10_1.line.color.rgb = c_card_border

    tb10_1 = slide10.shapes.add_textbox(Inches(1.0), Inches(1.65), Inches(5.2), Inches(4.9))
    tf10_1 = tb10_1.text_frame
    tf10_1.word_wrap = True

    p = tf10_1.paragraphs[0]
    p.text = "■ ここまでの到達点（基盤確立）"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = c_cyan

    p = tf10_1.add_paragraph()
    p.text = "1. 実活動2日間でテキスト全3回分を完全走破:\n   - OpenFaceによる特徴抽出（頭部姿勢、AU、視線、瞬目）\n   - FACS/AUの解析と独自情動指標のモデリング\n   - 時系列差分・閾値イベント化・移動平均平滑化\n   - 4段Emotion Timelineの構築\n2. 独自同期アニメーションツールの完成 (3-WB.py):\n   - 動画と時系列グラフのリアルタイム同期検証基盤を確立\n3. データサイエンスとしての視座:\n   - Pixel → Feature → Behavior → State → Emotion の階層性を理解し、客観的現象と心理推定を分離して扱う素養を習得。"
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_light

    c10_2 = slide10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.9), Inches(1.45), Inches(5.6), Inches(5.3))
    c10_2.fill.solid()
    c10_2.fill.fore_color.rgb = c_card_bg
    c10_2.line.color.rgb = c_card_border

    tb10_2 = slide10.shapes.add_textbox(Inches(7.1), Inches(1.65), Inches(5.2), Inches(4.9))
    tf10_2 = tb10_2.text_frame
    tf10_2.word_wrap = True

    p = tf10_2.paragraphs[0]
    p.text = "■ 第4回 計画：『嘘発見器』の高度化＆アプリ開発"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = c_emerald

    p = tf10_2.add_paragraph()
    p.text = "1. 嘘発見（虚偽検出）の精度向上アプローチ:\n   ・多変量特徴の統合: まばたき急増(AU45)、視線の泳ぎ(gaze)、作り笑顔(AU12有/AU06無)、眉間の緊張(AU04)の複合解析\n   ・微表情（マイクロエクスプレッション）の差分検出\n   ・機械学習の導入: scikit-learnによる真実回答時 vs 虚偽回答時の分類モデル（SVM/Random Forest）学習\n2. 実用的な『嘘発見アプリ』の開発:\n   ・3-WB.pyの同期技術を発展させ、リアルタイムカメラ映像から「嘘らしさスコア(Deception Index)」を即時判定・描画するGUIアプリを実装\n   ・質問提示と連動した自動アノテーション・判定UIの構築"
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_light

    # Save to BOTH slides.pptx and progress_report.pptx
    prs.save("slides.pptx")
    prs.save("progress_report.pptx")
    print("Presentation saved successfully to slides.pptx and progress_report.pptx!")

if __name__ == "__main__":
    create_deck()
