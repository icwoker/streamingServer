from werkzeug.security import generate_password_hash,check_password_hash

class PasswordUtils:

    def hash_password(self,password:str)->str:
        """
        对密码进行哈希加密码:
        :param password: 明文密码
        :return:加密密码
        """
        return generate_password_hash(password)

    @staticmethod
    def verify_password(password:str,hashed_password:str)->bool:
        """
        验证密码是否正确:
        :param password: 明文密码
        :param hashed_password: 加密密码
        :return: 布尔值
        """
        return check_password_hash(hashed_password,password)