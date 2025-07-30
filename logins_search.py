import os
import json
import re
import urllib3
from sseclient import SSEClient
import json
import re
import urllib3
from sseclient import SSEClient

class LoginSearch:
    def __init__(self, url, id_user, pasta_temp, cancel_flag, contador_callback=None):
        self.url = url
        self.id_user = id_user
        self.pasta_temp = pasta_temp
        self.cancel_flag = cancel_flag
        self.contador_callback = contador_callback
        os.makedirs(self.pasta_temp, exist_ok=True)

    def buscar(self):
        raw_path = os.path.join(self.pasta_temp, f"{self.id_user}.txt")
        formatado_path = os.path.join(self.pasta_temp, f"{self.id_user}_formatado.txt")

        contador = 0
        limite = 80000
        regex_valido = re.compile(r'^[a-zA-Z0-9!@#$%^&*()\-_=+\[\]{}|;:\'\",.<>/?`~\\]+$')

        http = urllib3.PoolManager()

        try:
            response = http.request('GET', f"https://patronhost.online/logs/api_sse.php?url={self.url}", preload_content=False)
            client = SSEClient(response)

            with open(raw_path, "w", encoding="utf-8") as f_raw, open(formatado_path, "w", encoding="utf-8") as f_fmt:
                for event in client.events():
                    if self.cancel_flag.get('cancelled'):
                        break
                    if contador >= limite:
                        break
                    try:
                        data = json.loads(event.data)
                        url_ = data.get("url", "")
                        user = data.get("user", "")
                        passwd = data.get("pass", "")
                        if url_ and user and passwd and user.upper() != "EMPTY":
                            user_limpo = ''.join(ch for ch in user if regex_valido.match(ch)).replace(" ", "")
                            passwd_limpo = ''.join(ch for ch in passwd if regex_valido.match(ch)).replace(" ", "")
                            if user_limpo and passwd_limpo:
                                f_raw.write(f"{user_limpo}:{passwd_limpo}\n")
                                f_fmt.write(f"\u2022 URL: {url_}\n\u2022 USU\u00c1RIO: {user_limpo}\n\u2022 SENHA: {passwd_limpo}\n\n")
                                contador += 1
                                if self.contador_callback:
                                    self.contador_callback(contador)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        finally:
            if 'response' in locals():
                response.release_conn()

        return raw_path, formatado_path

    
