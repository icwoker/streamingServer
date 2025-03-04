import os

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB


def allowed_image(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_image_size(file):
    if file and file.content_length > MAX_CONTENT_LENGTH:
        return False
    return True

def check_image(file):
    return check_image_size(file) and allowed_image(file.filename)


def save_image(file, base_path, filename):
    # 检查图片格式和大小 (假设 check_image 函数已定义)
    if not check_image(file):
        return '图片格式或大小不正确，请修改后重新上传！'

    # 构建完整的文件路径
    file_path = os.path.join(base_path, filename)

    # 确保基本路径存在
    if not os.path.exists(base_path):
        try:
            os.makedirs(base_path)  # 递归创建目录
        except OSError as e:
            return f'创建目录失败: {e}'

    # 保存文件
    try:
        with open(file_path, 'wb') as f:  # 以二进制写入模式打开文件
            f.write(file.read())  # 将文件内容写入
        return '图片上传成功！'
    except Exception as e:
        return f'保存文件失败: {e}'