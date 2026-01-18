import wx
import os
import sys
import subprocess
import zipfile
import time

# 配置信息
TITLE = "仿mac安装程序"
DRAG_DATA_ID = "MY_MAC_INSTALLER_DROP"


def get_resource_path(relative_path):
    """获取资源的绝对路径，适配打包后的环境"""
    try:
        # PyInstaller 打包后的临时路径
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def manual_wrap(text, width=50):
    """根据字符长度对字符串进行逻辑换行，用于美化浮窗内容"""
    if len(text) <= width:
        return text
    lines = [text[i:i+width] for i in range(0, len(text), width)]
    return '\n'.join(lines)


class InstallDropTarget(wx.TextDropTarget):
    """处理拖拽释放逻辑"""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def OnDropText(self, x, y, data):
        if data == DRAG_DATA_ID:
            self.callback()
            return True
        return False


class DraggableStaticBitmap(wx.StaticBitmap):
    """可拖拽的 APP 图标"""
    def __init__(self, parent, id, bitmap, warning_callback):
        super().__init__(parent, id, bitmap)
        self.warning_callback = warning_callback
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)

    def OnLeftDown(self, event):
        text_data = wx.TextDataObject(DRAG_DATA_ID)
        drop_source = wx.DropSource(self)
        drop_source.SetData(text_data)
        result = drop_source.DoDragDrop(wx.Drag_CopyOnly)
        if result == wx.DragNone:
            self.warning_callback()
        event.Skip()


class ClickableStaticBitmap(wx.StaticBitmap):
    """可点击的文件夹图标"""
    def __init__(self, parent, id, bitmap, click_callback):
        super().__init__(parent, id, bitmap)
        self.click_callback = click_callback
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))

    def OnLeftDown(self, event):
        self.click_callback()


class MacInstallerFrame(wx.Frame):
    def __init__(self):
        # 禁用最大化按钮：移除 wx.MAXIMIZE_BOX 样式
        style = wx.DEFAULT_FRAME_STYLE & ~(wx.MAXIMIZE_BOX)
        super().__init__(None, title=TITLE, size=(600, 350), style=style)

        self.SetBackgroundColour(wx.Colour(240, 240, 240))
        self.set_window_icon()

        # 初始化安装路径
        self.install_path = os.path.join(os.path.expanduser("~"), "Applications")
        if not os.path.exists(self.install_path):
            os.makedirs(self.install_path)

        self.init_ui()
        self.Center()

    def set_window_icon(self):
        """设置窗口小图标"""
        icon_path = get_resource_path("app.png")
        if os.path.exists(icon_path):
            try:
                image = wx.Image(icon_path, wx.BITMAP_TYPE_ANY)
                if image.IsOk():
                    icon = wx.Icon()
                    icon.CopyFromBitmap(wx.Bitmap(image))
                    self.SetIcon(icon)
            except Exception as e:
                print(f"Icon loading error: {e}")

    def init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        content_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 1. APP 图标 (左侧)
        img_app = self.get_app_bitmap()
        self.bmp_app = DraggableStaticBitmap(panel, -1, img_app, self.on_app_click)

        # 2. 箭头 (中间)
        arrow_label = wx.StaticText(panel, label="→")
        arrow_font = wx.Font(40, wx.FONTFAMILY_DEFAULT,
                             wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        arrow_label.SetFont(arrow_font)
        arrow_label.SetForegroundColour(wx.Colour(150, 150, 150))

        # 3. 文件夹区域 (右侧)
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        img_folder = wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, (96, 96))
        self.bmp_folder = ClickableStaticBitmap(panel, -1, img_folder,
                                                self.open_target_folder)
        self.bmp_folder.SetDropTarget(InstallDropTarget(self.on_drop_install))

        # 【核心修改】：设置浮窗显示路径 (ToolTip)
        self.update_folder_tooltip()

        self.btn_path = wx.Button(panel, label="更改路径")
        self.btn_path.Bind(wx.EVT_BUTTON, self.on_change_path)

        right_sizer.Add(self.bmp_folder, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        right_sizer.Add(self.btn_path, 0, wx.ALIGN_CENTER)

        # 组合布局
        content_sizer.Add(self.bmp_app, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 40)
        content_sizer.Add(arrow_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 40)
        content_sizer.Add(right_sizer, 0, wx.ALIGN_CENTER_VERTICAL)

        main_sizer.Add(content_sizer, 1, wx.ALIGN_CENTER | wx.ALL, 30)

        # 底部提示语
        tip_label = wx.StaticText(panel, label="将图标拖入文件夹以安装")
        tip_label.SetForegroundColour(wx.Colour(120, 120, 120))
        main_sizer.Add(tip_label, 0, wx.ALIGN_CENTER | wx.BOTTOM, 20)

        panel.SetSizer(main_sizer)

    def update_folder_tooltip(self):
        """更新文件夹图标的悬停浮窗内容"""
        # 使用 manual_wrap 确保浮窗里的路径过长时会自动换行
        tip_content = f"当前安装位置：\n{manual_wrap(self.install_path, 40)}"
        self.bmp_folder.SetToolTip(wx.ToolTip(tip_content))

    def get_app_bitmap(self):
        """获取或生成 APP 图标位图"""
        icon_path = get_resource_path("app.png")
        if os.path.exists(icon_path):
            img = wx.Image(icon_path, wx.BITMAP_TYPE_ANY)
            if img.IsOk():
                return wx.Bitmap(img.Scale(96, 96, wx.IMAGE_QUALITY_HIGH))
        return wx.Bitmap(96, 96)

    def on_app_click(self):
        """处理点击图标而非拖拽的情况"""
        wx.MessageBox("请拖动 APP 图标到右侧文件夹中完成安装。", "操作提示")

    def open_target_folder(self):
        """打开当前设定的安装目录"""
        if not os.path.exists(self.install_path):
            return

        try:
            if sys.platform == 'win32':
                os.startfile(self.install_path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', self.install_path])
            else:
                subprocess.Popen(['xdg-open', self.install_path])
        except Exception as e:
            print(f"Failed to open folder: {e}")

    def on_change_path(self, event):
        """修改安装路径"""
        dlg = wx.DirDialog(self, "选择安装目录", self.install_path)
        if dlg.ShowModal() == wx.ID_OK:
            self.install_path = dlg.GetPath()
            self.update_folder_tooltip()
        dlg.Destroy()

    def on_drop_install(self):
        """执行 zipfile 解压安装逻辑"""
        zip_path = get_resource_path("app.zip")
        if not os.path.exists(zip_path):
            wx.MessageBox("错误：未能在安装包内找到资源文件 (app.zip)。",
                          "安装失败", wx.ICON_ERROR)
            return

        pd = wx.ProgressDialog("正在安装", "正在释放资源...", 100, self,
                               style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                file_list = zf.namelist()
                total = len(file_list)

                for i, filename in enumerate(file_list):
                    zf.extract(filename, self.install_path)
                    # 更新进度
                    progress = int(((i + 1) / total) * 100)
                    pd.Update(progress, f"正在解压: {filename}")
                    # time.sleep 确保 UI 能够平滑刷新，并消除 unused 警告
                    time.sleep(0.02)

            pd.Destroy()
            wx.MessageBox(f"成功安装至：\n{self.install_path}", "完成")
            self.open_target_folder()

        except Exception as e:
            if pd:
                pd.Destroy()
            wx.MessageBox(f"解压失败：{str(e)}", "错误", wx.ICON_ERROR)


if __name__ == '__main__':
    app = wx.App()
    frame = MacInstallerFrame()
    frame.Show()
    app.MainLoop()
