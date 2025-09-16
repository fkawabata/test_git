import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
import difflib
from typing import List, Tuple, Dict
import re


class XMLComparator:
    """XMLファイルを比較するためのクラス"""
    
    def __init__(self):
        self.xml1_sections = []
        self.xml2_sections = []
    
    def parse_xml(self, file_path: str) -> List[Dict]:
        """XMLファイルを解析してセクションのリストを返す"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            sections = []
            
            # ルート要素の直下の子要素をセクションとして扱う
            for child in root:
                section = {
                    'tag': child.tag,
                    'text': self._get_text_content(child)
                }
                sections.append(section)
            
            return sections
        except Exception as e:
            raise Exception(f"XMLファイルの解析エラー: {str(e)}")
    
    def _get_text_content(self, element: ET.Element) -> str:
        """要素からテキストコンテンツのみを抽出（属性は無視）"""
        text_parts = []
        
        # 要素自身のテキスト
        if element.text and element.text.strip():
            text_parts.append(element.text.strip())
        
        # 子要素のテキストを再帰的に取得
        for child in element:
            child_text = self._get_text_content(child)
            if child_text:
                text_parts.append(child_text)
            
            # 子要素の後のテキスト（tail）
            if child.tail and child.tail.strip():
                text_parts.append(child.tail.strip())
        
        return ' '.join(text_parts)
    
    def compare_characters(self, text1: str, text2: str) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """2つのテキストを文字レベルで比較して差分位置を返す"""
        # 文字単位で比較
        matcher = difflib.SequenceMatcher(None, text1, text2)
        
        # 差分位置を収集
        diff_positions1 = []
        diff_positions2 = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'delete' or tag == 'replace':
                # text1の差分位置
                diff_positions1.append((i1, i2))
            if tag == 'insert' or tag == 'replace':
                # text2の差分位置
                diff_positions2.append((j1, j2))
        
        return diff_positions1, diff_positions2


class XMLComparisonGUI:
    """XML比較用のGUIアプリケーション"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("XML文書比較ツール")
        self.root.geometry("1400x800")
        
        self.comparator = XMLComparator()
        self.xml1_path = None
        self.xml2_path = None
        self.section_frames = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """UIコンポーネントを設定"""
        # メニューバー
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="XML 1を開く", command=lambda: self.load_xml(1))
        file_menu.add_command(label="XML 2を開く", command=lambda: self.load_xml(2))
        file_menu.add_separator()
        file_menu.add_command(label="比較実行", command=self.compare_xmls)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
        
        # ツールバー
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="XML 1を開く", command=lambda: self.load_xml(1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="XML 2を開く", command=lambda: self.load_xml(2)).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="比較実行", command=self.compare_xmls).pack(side=tk.LEFT, padx=10)
        
        # ファイルパス表示
        path_frame = ttk.Frame(self.root)
        path_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        ttk.Label(path_frame, text="XML 1:").pack(side=tk.LEFT)
        self.path1_label = ttk.Label(path_frame, text="未選択", foreground="gray")
        self.path1_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(path_frame, text="｜ XML 2:").pack(side=tk.LEFT, padx=20)
        self.path2_label = ttk.Label(path_frame, text="未選択", foreground="gray")
        self.path2_label.pack(side=tk.LEFT, padx=5)
        
        # メインコンテンツエリア（スクロール可能）
        self.create_scrollable_area()
    
    def create_scrollable_area(self):
        """スクロール可能なコンテンツエリアを作成"""
        # Canvas とスクロールバーを含むフレーム
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # スクロールバー
        v_scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scrollbar = ttk.Scrollbar(container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Canvas
        self.canvas = tk.Canvas(container, 
                               yscrollcommand=v_scrollbar.set,
                               xscrollcommand=h_scrollbar.set,
                               bg='white')
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        v_scrollbar.config(command=self.canvas.yview)
        h_scrollbar.config(command=self.canvas.xview)
        
        # Canvas内のフレーム
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), 
                                                       window=self.scrollable_frame, 
                                                       anchor="nw")
        
        # フレームのサイズが変更されたときにスクロール領域を更新
        self.scrollable_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
    
    def on_frame_configure(self, event):
        """フレームのサイズが変更されたときの処理"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        """Canvasのサイズが変更されたときの処理"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def load_xml(self, xml_number: int):
        """XMLファイルを読み込む"""
        file_path = filedialog.askopenfilename(
            title=f"XML {xml_number}を選択",
            filetypes=[("XMLファイル", "*.xml"), ("すべてのファイル", "*.*")]
        )
        
        if file_path:
            if xml_number == 1:
                self.xml1_path = file_path
                self.path1_label.config(text=file_path.split('/')[-1], foreground="black")
            else:
                self.xml2_path = file_path
                self.path2_label.config(text=file_path.split('/')[-1], foreground="black")
    
    def compare_xmls(self):
        """2つのXMLファイルを比較"""
        if not self.xml1_path or not self.xml2_path:
            messagebox.showwarning("警告", "2つのXMLファイルを選択してください．")
            return
        
        try:
            # 既存の比較結果をクリア
            self.clear_comparison()
            
            # XMLファイルを解析
            sections1 = self.comparator.parse_xml(self.xml1_path)
            sections2 = self.comparator.parse_xml(self.xml2_path)
            
            # セクション数を合わせる
            max_sections = max(len(sections1), len(sections2))
            
            # 各セクションを比較して表示
            for i in range(max_sections):
                section1 = sections1[i] if i < len(sections1) else {'tag': '(なし)', 'text': ''}
                section2 = sections2[i] if i < len(sections2) else {'tag': '(なし)', 'text': ''}
                
                self.display_section_comparison(i, section1, section2)
            
        except Exception as e:
            messagebox.showerror("エラー", str(e))
    
    def clear_comparison(self):
        """比較結果をクリア"""
        for frame in self.section_frames:
            frame.destroy()
        self.section_frames.clear()
    
    def display_section_comparison(self, index: int, section1: dict, section2: dict):
        """セクションの比較結果を表示"""
        # セクションフレーム
        section_frame = ttk.LabelFrame(self.scrollable_frame, 
                                       text=f"セクション {index + 1}: {section1['tag']} / {section2['tag']}",
                                       padding=10)
        section_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.section_frames.append(section_frame)
        
        # 左右のテキストエリアを含むフレーム
        content_frame = ttk.Frame(section_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左側（XML 1）
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        ttk.Label(left_frame, text="XML 1", font=('Arial', 10, 'bold')).pack()
        text_left = tk.Text(left_frame, wrap=tk.WORD, height=10, width=60)
        text_left.pack(fill=tk.BOTH, expand=True)
        
        # 右側（XML 2）
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        ttk.Label(right_frame, text="XML 2", font=('Arial', 10, 'bold')).pack()
        text_right = tk.Text(right_frame, wrap=tk.WORD, height=10, width=60)
        text_right.pack(fill=tk.BOTH, expand=True)
        
        # 文字レベルで差分をハイライト
        self.highlight_word_differences(text_left, text_right, section1['text'], section2['text'])
    
    def highlight_word_differences(self, text_widget1: tk.Text, text_widget2: tk.Text, 
                                  content1: str, content2: str):
        """文字レベルで差分をハイライト表示"""
        # タグの設定
        text_widget1.tag_configure("diff", background="#ffcccc")
        text_widget2.tag_configure("diff", background="#ffcccc")
        
        # 文字レベルで差分位置を取得
        diff_positions1, diff_positions2 = self.comparator.compare_characters(content1, content2)
        
        # テキストを挿入
        text_widget1.insert('1.0', content1)
        text_widget2.insert('1.0', content2)
        
        # 差分部分にタグを適用
        for start, end in diff_positions1:
            text_widget1.tag_add("diff", f"1.0 +{start}c", f"1.0 +{end}c")
        
        for start, end in diff_positions2:
            text_widget2.tag_add("diff", f"1.0 +{start}c", f"1.0 +{end}c")
        
        # テキストウィジェットを読み取り専用に
        text_widget1.config(state=tk.DISABLED)
        text_widget2.config(state=tk.DISABLED)
    
    def run(self):
        """アプリケーションを実行"""
        self.root.mainloop()


def create_sample_xml(filename: str, sections: List[Tuple[str, str]]):
    """テスト用のサンプルXMLファイルを作成"""
    root = ET.Element("document")
    
    for tag, content in sections:
        section = ET.SubElement(root, tag)
        section.text = content
    
    tree = ET.ElementTree(root)
    tree.write(filename, encoding='utf-8', xml_declaration=True)
    print(f"サンプルファイル '{filename}' を作成しました．")


def create_test_files():
    """テスト用のXMLファイルを作成"""
    # サンプル1
    sections1 = [
        ("introduction", "これは最初のセクションです．XMLファイルの比較テストを行います．"),
        ("main", "メインセクションには重要な情報が含まれています．複数の文章があります．"),
        ("conclusion", "結論として，このツールは便利です．"),
        ("appendix", "追加情報をここに記載します．")
    ]
    create_sample_xml("sample1.xml", sections1)
    
    # サンプル2（一部異なる）
    sections2 = [
        ("introduction", "これは最初のセクションです．XMLドキュメントの比較テストを実施します．"),
        ("main", "メインセクションには重要なデータが含まれています．いくつかの文章があります．"),
        ("conclusion", "まとめとして，このツールは非常に便利です．"),
        ("appendix", "追加情報をここに記載します．")
    ]
    create_sample_xml("sample2.xml", sections2)


if __name__ == "__main__":
    import sys
    
    # コマンドライン引数で --test を指定した場合，テストファイルを作成
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        create_test_files()
        print("\nテストファイルを作成しました．")
        print("プログラムを通常実行して，sample1.xml と sample2.xml を比較してください．")
    else:
        app = XMLComparisonGUI()
        app.run()