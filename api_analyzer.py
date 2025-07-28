
import requests
import re
import json
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

class AdvancedAPIAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-US;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
        self.discovered_apis = []
        self.endpoints = set()
        self.forms = []
        self.js_apis = []
        self.network_requests = []
        self.cookies = {}
        
    def comprehensive_api_discovery(self, url):
        """Análise completa de APIs usando múltiplas técnicas"""
        print(f"🚀 Iniciando análise completa de APIs para: {url}")
        
        results = {
            "target_url": url,
            "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "discovered_apis": [],
            "endpoints": [],
            "forms": [],
            "javascript_apis": [],
            "network_patterns": [],
            "security_analysis": {},
            "api_documentation": [],
            "swagger_openapi": [],
            "rest_patterns": [],
            "graphql_endpoints": [],
            "websocket_endpoints": [],
            "authentication_methods": [],
            "rate_limiting": {},
            "cors_analysis": {},
            "common_vulnerabilities": []
        }
        
        try:
            # 1. Análise da página principal
            print("📄 Analisando página principal...")
            main_response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(main_response.text, 'html.parser')
            
            # 2. Descobrir endpoints em JavaScript
            print("🔍 Extraindo endpoints do JavaScript...")
            js_endpoints = self._extract_js_endpoints(soup, url)
            results["javascript_apis"] = js_endpoints
            
            # 3. Analisar formulários e campos
            print("📝 Analisando formulários...")
            forms_data = self._analyze_forms(soup, url)
            results["forms"] = forms_data
            
            # 4. Procurar documentação de API
            print("📚 Procurando documentação de APIs...")
            api_docs = self._find_api_documentation(soup, url)
            results["api_documentation"] = api_docs
            
            # 5. Descobrir Swagger/OpenAPI
            print("📋 Verificando Swagger/OpenAPI...")
            swagger_data = self._discover_swagger_openapi(url)
            results["swagger_openapi"] = swagger_data
            
            # 6. Testar endpoints comuns
            print("🎯 Testando endpoints comuns...")
            common_endpoints = self._test_common_api_endpoints(url)
            results["endpoints"] = common_endpoints
            
            # 7. Análise de padrões REST
            print("🌐 Analisando padrões REST...")
            rest_patterns = self._analyze_rest_patterns(url, js_endpoints)
            results["rest_patterns"] = rest_patterns
            
            # 8. Procurar GraphQL
            print("⚡ Verificando GraphQL...")
            graphql_endpoints = self._discover_graphql(url)
            results["graphql_endpoints"] = graphql_endpoints
            
            # 9. Procurar WebSockets
            print("🔌 Verificando WebSockets...")
            websocket_endpoints = self._discover_websockets(soup, js_endpoints)
            results["websocket_endpoints"] = websocket_endpoints
            
            # 10. Análise de autenticação
            print("🔐 Analisando métodos de autenticação...")
            auth_methods = self._analyze_authentication(soup, js_endpoints)
            results["authentication_methods"] = auth_methods
            
            # 11. Análise de CORS
            print("🌍 Verificando CORS...")
            cors_analysis = self._analyze_cors(url)
            results["cors_analysis"] = cors_analysis
            
            # 12. Buscar vulnerabilidades comuns
            print("🛡️ Verificando vulnerabilidades...")
            vulnerabilities = self._check_common_vulnerabilities(url, results)
            results["common_vulnerabilities"] = vulnerabilities
            
            # 13. Análise de rate limiting
            print("⏱️ Testando rate limiting...")
            rate_limiting = self._test_rate_limiting(url)
            results["rate_limiting"] = rate_limiting
            
            # 14. Mapear estrutura de APIs
            print("🗺️ Mapeando estrutura completa...")
            self._map_api_structure(results)
            
            print("✅ Análise completa finalizada!")
            return results
            
        except Exception as e:
            return {"error": f"Erro na análise: {str(e)}"}
    
    def _extract_js_endpoints(self, soup, base_url):
        """Extrai endpoints de arquivos JavaScript"""
        js_endpoints = []
        
        # Encontrar arquivos JS
        js_files = []
        for script in soup.find_all('script', src=True):
            js_url = urljoin(base_url, script['src'])
            js_files.append(js_url)
        
        # Também analisar JS inline
        inline_scripts = []
        for script in soup.find_all('script'):
            if script.string:
                inline_scripts.append(script.string)
        
        # Padrões para detectar APIs
        api_patterns = [
            r'["\']\/api\/[^"\']*["\']',
            r'["\']\/v\d+\/[^"\']*["\']',
            r'["\']https?://[^"\']*\/api\/[^"\']*["\']',
            r'fetch\(["\']([^"\']+)["\']',
            r'axios\.[a-z]+\(["\']([^"\']+)["\']',
            r'\$\.ajax\(\{[^}]*url\s*:\s*["\']([^"\']+)["\']',
            r'XMLHttpRequest.*open\(["\'][^"\']*["\'],\s*["\']([^"\']+)["\']',
            r'endpoint["\s]*[:=]\s*["\']([^"\']+)["\']',
            r'baseURL["\s]*[:=]\s*["\']([^"\']+)["\']',
            r'apiUrl["\s]*[:=]\s*["\']([^"\']+)["\']',
            r'["\']\/graphql["\']',
            r'["\']\/ws\/[^"\']*["\']',
            r'["\']\/socket\.io\/[^"\']*["\']'
        ]
        
        # Analisar arquivos JS externos
        for js_url in js_files[:10]:  # Limitar para não sobrecarregar
            try:
                js_response = self.session.get(js_url, timeout=10)
                js_content = js_response.text
                
                for pattern in api_patterns:
                    matches = re.findall(pattern, js_content, re.IGNORECASE)
                    for match in matches:
                        endpoint = match if isinstance(match, str) else match[0] if match else ""
                        if endpoint and self._is_valid_endpoint(endpoint):
                            js_endpoints.append({
                                "endpoint": endpoint,
                                "source": js_url,
                                "type": "external_js"
                            })
            except:
                continue
        
        # Analisar JS inline
        for script_content in inline_scripts:
            for pattern in api_patterns:
                matches = re.findall(pattern, script_content, re.IGNORECASE)
                for match in matches:
                    endpoint = match if isinstance(match, str) else match[0] if match else ""
                    if endpoint and self._is_valid_endpoint(endpoint):
                        js_endpoints.append({
                            "endpoint": endpoint,
                            "source": "inline_script",
                            "type": "inline_js"
                        })
        
        return js_endpoints
    
    def _analyze_forms(self, soup, base_url):
        """Análise detalhada de formulários"""
        forms_data = []
        
        for form in soup.find_all('form'):
            form_data = {
                "action": urljoin(base_url, form.get('action', '')),
                "method": form.get('method', 'GET').upper(),
                "fields": [],
                "hidden_fields": [],
                "file_uploads": [],
                "csrf_tokens": [],
                "api_potential": False
            }
            
            # Analisar campos
            for input_field in form.find_all(['input', 'textarea', 'select']):
                field_info = {
                    "name": input_field.get('name', ''),
                    "type": input_field.get('type', 'text'),
                    "value": input_field.get('value', ''),
                    "required": input_field.has_attr('required'),
                    "placeholder": input_field.get('placeholder', '')
                }
                
                if field_info["type"] == "hidden":
                    form_data["hidden_fields"].append(field_info)
                    if any(token in field_info["name"].lower() for token in ['csrf', 'token', '_token']):
                        form_data["csrf_tokens"].append(field_info)
                elif field_info["type"] == "file":
                    form_data["file_uploads"].append(field_info)
                else:
                    form_data["fields"].append(field_info)
            
            # Verificar se parece com API
            if any(api_word in form_data["action"].lower() for api_word in ['api', 'ajax', 'json']):
                form_data["api_potential"] = True
            
            forms_data.append(form_data)
        
        return forms_data
    
    def _find_api_documentation(self, soup, base_url):
        """Procura por documentação de APIs"""
        api_docs = []
        
        # Links que podem ser documentação
        doc_patterns = [
            r'api',
            r'docs',
            r'documentation',
            r'swagger',
            r'postman',
            r'openapi',
            r'developer',
            r'reference'
        ]
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()
            
            for pattern in doc_patterns:
                if pattern in href.lower() or pattern in text:
                    api_docs.append({
                        "url": urljoin(base_url, href),
                        "text": text.strip(),
                        "type": "documentation_link"
                    })
        
        return api_docs
    
    def _discover_swagger_openapi(self, base_url):
        """Procura por Swagger/OpenAPI"""
        swagger_paths = [
            '/swagger',
            '/swagger-ui',
            '/swagger-ui.html',
            '/swagger/index.html',
            '/api-docs',
            '/api/docs',
            '/docs',
            '/documentation',
            '/swagger.json',
            '/swagger.yaml',
            '/openapi.json',
            '/openapi.yaml',
            '/api/swagger.json',
            '/api/swagger.yaml',
            '/v1/swagger.json',
            '/v2/swagger.json'
        ]
        
        swagger_data = []
        
        for path in swagger_paths:
            try:
                test_url = urljoin(base_url, path)
                response = self.session.get(test_url, timeout=5)
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '').lower()
                    
                    if 'json' in content_type:
                        try:
                            data = response.json()
                            if 'swagger' in data or 'openapi' in data:
                                swagger_data.append({
                                    "url": test_url,
                                    "type": "swagger_json",
                                    "version": data.get('swagger') or data.get('openapi'),
                                    "title": data.get('info', {}).get('title', ''),
                                    "endpoints_count": len(data.get('paths', {}))
                                })
                        except:
                            pass
                    
                    elif 'html' in content_type:
                        if any(term in response.text.lower() for term in ['swagger', 'openapi', 'api documentation']):
                            swagger_data.append({
                                "url": test_url,
                                "type": "swagger_ui",
                                "accessible": True
                            })
            except:
                continue
        
        return swagger_data
    
    def _test_common_api_endpoints(self, base_url):
        """Testa endpoints comuns de API"""
        common_paths = [
            '/api',
            '/api/v1',
            '/api/v2',
            '/api/v3',
            '/v1',
            '/v2',
            '/v3',
            '/rest',
            '/rest/api',
            '/webservice',
            '/ws',
            '/service',
            '/services',
            '/json',
            '/ajax',
            '/api.php',
            '/api.json',
            '/api/status',
            '/api/health',
            '/api/ping',
            '/api/version',
            '/api/info',
            '/api/users',
            '/api/auth',
            '/api/login',
            '/api/data',
            '/graphql',
            '/graph',
            '/query'
        ]
        
        working_endpoints = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {
                executor.submit(self._test_endpoint, urljoin(base_url, path)): path 
                for path in common_paths
            }
            
            for future in as_completed(future_to_url):
                path = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        working_endpoints.append(result)
                except:
                    continue
        
        return working_endpoints
    
    def _test_endpoint(self, url):
        """Testa um endpoint específico"""
        try:
            response = self.session.get(url, timeout=5)
            
            if response.status_code not in [404, 403]:
                content_type = response.headers.get('Content-Type', '').lower()
                
                result = {
                    "url": url,
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "response_size": len(response.content),
                    "headers": dict(response.headers),
                    "is_json": False,
                    "is_xml": False,
                    "requires_auth": False
                }
                
                # Verificar tipo de resposta
                if 'json' in content_type:
                    result["is_json"] = True
                    try:
                        result["json_sample"] = response.json()
                    except:
                        pass
                elif 'xml' in content_type:
                    result["is_xml"] = True
                
                # Verificar se requer autenticação
                if response.status_code in [401, 403]:
                    result["requires_auth"] = True
                
                return result
        except:
            return None
    
    def _analyze_rest_patterns(self, base_url, js_endpoints):
        """Analisa padrões REST"""
        rest_patterns = []
        
        # Padrões REST comuns
        rest_regex_patterns = [
            r'\/api\/\w+\/\d+',  # /api/users/123
            r'\/api\/\w+\/\w+\/\d+',  # /api/users/profile/123
            r'\/\w+\/\d+',  # /users/123
            r'\/\w+\/\w+\/\d+',  # /users/profile/123
        ]
        
        all_endpoints = [ep["endpoint"] for ep in js_endpoints] + list(self.endpoints)
        
        for endpoint in all_endpoints:
            for pattern in rest_regex_patterns:
                if re.search(pattern, endpoint):
                    rest_patterns.append({
                        "endpoint": endpoint,
                        "pattern": pattern,
                        "type": "rest_resource",
                        "potential_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"]
                    })
        
        return rest_patterns
    
    def _discover_graphql(self, base_url):
        """Procura por endpoints GraphQL"""
        graphql_paths = [
            '/graphql',
            '/graph',
            '/query',
            '/api/graphql',
            '/v1/graphql',
            '/graphiql'
        ]
        
        graphql_endpoints = []
        
        for path in graphql_paths:
            try:
                test_url = urljoin(base_url, path)
                
                # Teste POST com query simples
                graphql_query = {
                    "query": "{ __schema { types { name } } }"
                }
                
                response = self.session.post(
                    test_url, 
                    json=graphql_query,
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if 'data' in data or 'errors' in data:
                            graphql_endpoints.append({
                                "url": test_url,
                                "type": "graphql",
                                "accessible": True,
                                "introspection_enabled": '__schema' in str(data)
                            })
                    except:
                        pass
                
                # Teste GET para GraphiQL
                get_response = self.session.get(test_url, timeout=5)
                if get_response.status_code == 200 and 'graphiql' in get_response.text.lower():
                    graphql_endpoints.append({
                        "url": test_url,
                        "type": "graphiql_interface",
                        "accessible": True
                    })
                    
            except:
                continue
        
        return graphql_endpoints
    
    def _discover_websockets(self, soup, js_endpoints):
        """Procura por WebSockets"""
        websocket_endpoints = []
        
        # Padrões WebSocket em JS
        ws_patterns = [
            r'new\s+WebSocket\(["\']([^"\']+)["\']',
            r'socket\.io[^"\']*["\']([^"\']+)["\']',
            r'ws://[^"\']+',
            r'wss://[^"\']+',
            r'\/socket\.io\/',
            r'\/ws\/',
            r'\/websocket\/'
        ]
        
        # Verificar nos endpoints JS encontrados
        for endpoint_data in js_endpoints:
            endpoint = endpoint_data["endpoint"]
            if any(ws_term in endpoint.lower() for ws_term in ['ws', 'socket', 'websocket']):
                websocket_endpoints.append({
                    "endpoint": endpoint,
                    "type": "websocket",
                    "source": endpoint_data["source"]
                })
        
        return websocket_endpoints
    
    def _analyze_authentication(self, soup, js_endpoints):
        """Analisa métodos de autenticação"""
        auth_methods = []
        
        # Procurar por formulários de login
        for form in soup.find_all('form'):
            inputs = form.find_all('input')
            input_types = [inp.get('type', '') for inp in inputs]
            input_names = [inp.get('name', '').lower() for inp in inputs]
            
            if 'password' in input_types or any(auth_term in ' '.join(input_names) for auth_term in ['password', 'login', 'username', 'email']):
                auth_methods.append({
                    "type": "form_based",
                    "action": form.get('action', ''),
                    "method": form.get('method', 'GET'),
                    "fields": input_names
                })
        
        # Procurar por padrões de token nos JS
        for endpoint_data in js_endpoints:
            endpoint = endpoint_data["endpoint"]
            if any(auth_term in endpoint.lower() for auth_term in ['auth', 'login', 'token', 'jwt', 'oauth']):
                auth_methods.append({
                    "type": "api_based",
                    "endpoint": endpoint,
                    "source": endpoint_data["source"]
                })
        
        # Verificar headers de autenticação comuns
        auth_headers = ['authorization', 'x-api-key', 'x-auth-token', 'x-access-token']
        for header in auth_headers:
            # Teste básico para ver se o header é esperado
            auth_methods.append({
                "type": "header_based",
                "header": header,
                "potential": True
            })
        
        return auth_methods
    
    def _analyze_cors(self, base_url):
        """Análise de CORS"""
        cors_analysis = {}
        
        try:
            # Fazer uma requisição OPTIONS
            response = self.session.options(base_url, timeout=5)
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
                'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
            }
            
            cors_analysis = {
                "cors_enabled": any(cors_headers.values()),
                "headers": {k: v for k, v in cors_headers.items() if v},
                "wildcard_origin": cors_headers.get('Access-Control-Allow-Origin') == '*'
            }
        except:
            cors_analysis = {"cors_enabled": False, "error": "Could not analyze CORS"}
        
        return cors_analysis
    
    def _check_common_vulnerabilities(self, base_url, results):
        """Verifica vulnerabilidades comuns"""
        vulnerabilities = []
        
        # Verificar CORS wildcard
        cors_data = results.get("cors_analysis", {})
        if cors_data.get("wildcard_origin"):
            vulnerabilities.append({
                "type": "CORS Wildcard",
                "severity": "Medium",
                "description": "Access-Control-Allow-Origin set to wildcard (*)"
            })
        
        # Verificar endpoints sem autenticação
        endpoints = results.get("endpoints", [])
        for endpoint in endpoints:
            if not endpoint.get("requires_auth") and endpoint.get("status_code") == 200:
                vulnerabilities.append({
                    "type": "Unauthenticated Endpoint",
                    "severity": "Low",
                    "description": f"Endpoint {endpoint['url']} accessible without authentication"
                })
        
        # Verificar documentação Swagger exposta
        swagger_data = results.get("swagger_openapi", [])
        for swagger in swagger_data:
            if swagger.get("accessible"):
                vulnerabilities.append({
                    "type": "Exposed API Documentation",
                    "severity": "Low",
                    "description": f"API documentation accessible at {swagger['url']}"
                })
        
        return vulnerabilities
    
    def _test_rate_limiting(self, base_url):
        """Testa rate limiting"""
        rate_limiting = {}
        
        try:
            # Fazer várias requisições rápidas
            start_time = time.time()
            responses = []
            
            for i in range(10):
                response = self.session.get(base_url, timeout=5)
                responses.append({
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                })
                time.sleep(0.1)
            
            end_time = time.time()
            
            # Verificar se alguma foi limitada
            rate_limited = any(r["status_code"] == 429 for r in responses)
            
            rate_limiting = {
                "rate_limited": rate_limited,
                "total_requests": len(responses),
                "time_taken": end_time - start_time,
                "responses": responses
            }
        except:
            rate_limiting = {"error": "Could not test rate limiting"}
        
        return rate_limiting
    
    def _map_api_structure(self, results):
        """Mapeia a estrutura completa das APIs"""
        # Organizar todos os endpoints descobertos
        all_endpoints = set()
        
        # Endpoints dos formulários
        for form in results.get("forms", []):
            if form.get("api_potential"):
                all_endpoints.add(form["action"])
        
        # Endpoints do JavaScript
        for js_api in results.get("javascript_apis", []):
            all_endpoints.add(js_api["endpoint"])
        
        # Endpoints testados
        for endpoint in results.get("endpoints", []):
            all_endpoints.add(endpoint["url"])
        
        # Endpoints GraphQL
        for gql in results.get("graphql_endpoints", []):
            all_endpoints.add(gql["url"])
        
        # Endpoints WebSocket
        for ws in results.get("websocket_endpoints", []):
            all_endpoints.add(ws["endpoint"])
        
        results["discovered_apis"] = list(all_endpoints)
        results["total_endpoints_found"] = len(all_endpoints)
    
    def _is_valid_endpoint(self, endpoint):
        """Verifica se um endpoint é válido"""
        if not endpoint or len(endpoint) < 2:
            return False
        
        # Filtrar URLs inválidas
        invalid_patterns = [
            r'^javascript:',
            r'^mailto:',
            r'^tel:',
            r'^#',
            r'\.(css|js|png|jpg|jpeg|gif|ico|svg|pdf|zip)(\?|$)',
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, endpoint, re.IGNORECASE):
                return False
        
        return True
    
    def comprehensive_analysis_with_bypass(self, url):
        """Análise completa com bypass de captcha e extração de API keys"""
        print(f"🚀 Iniciando análise avançada com bypass para: {url}")
        
        results = {
            "target_url": url,
            "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "captcha_bypassed": False,
            "api_keys": [],
            "api_keys_found": 0,
            "discovered_apis": [],
            "endpoints": [],
            "forms": [],
            "javascript_apis": [],
            "network_patterns": [],
            "security_analysis": {},
            "api_documentation": [],
            "swagger_openapi": [],
            "rest_patterns": [],
            "graphql_endpoints": [],
            "websocket_endpoints": [],
            "authentication_methods": [],
            "rate_limiting": {},
            "cors_analysis": {},
            "common_vulnerabilities": []
        }
        
        try:
            # 1. Tentar bypass de proteções
            print("🛡️ Tentando bypass de proteções...")
            bypassed_session = self._bypass_protections(url)
            
            # 2. Análise da página com bypass
            print("📄 Analisando página com bypass...")
            main_response = bypassed_session.get(url, timeout=20)
            soup = BeautifulSoup(main_response.text, 'html.parser')
            
            # 3. Extrair API Keys primeiro
            print("🔑 Extraindo API Keys...")
            api_keys = self._extract_api_keys_advanced(soup, main_response.text, url)
            results["api_keys"] = api_keys
            results["api_keys_found"] = len(api_keys)
            
            # 4. Executar análise completa de APIs
            print("🔍 Executando análise completa de APIs...")
            api_analysis = self.comprehensive_api_discovery(url)
            
            # 5. Mesclar resultados
            for key in api_analysis:
                if key not in ["target_url", "analysis_timestamp"]:
                    results[key] = api_analysis[key]
            
            results["captcha_bypassed"] = "Sucesso" if bypassed_session else "Falhou"
            
            print("✅ Análise avançada concluída!")
            return results
            
        except Exception as e:
            return {"error": f"Erro na análise avançada: {str(e)}"}
    
    def _bypass_protections(self, url):
        """Tenta fazer bypass de proteções como Cloudflare, captchas, etc."""
        try:
            import cloudscraper
            
            # Usar cloudscraper para bypass de Cloudflare
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                }
            )
            
            # Headers avançados para bypass
            scraper.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-US;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            })
            
            # Teste de acesso
            test_response = scraper.get(url, timeout=15)
            if test_response.status_code == 200:
                print("✅ Bypass bem-sucedido!")
                return scraper
            else:
                print(f"⚠️ Bypass parcial (Status: {test_response.status_code})")
                return scraper
                
        except ImportError:
            print("⚠️ cloudscraper não disponível, usando sessão padrão")
            # Fallback para sessão normal com headers avançados
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-US;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            })
            return session
        except Exception as e:
            print(f"❌ Erro no bypass: {e}")
            return self.session
    
    def _extract_api_keys_advanced(self, soup, page_content, base_url):
        """Extração avançada de API Keys"""
        api_keys = []
        
        # Padrões avançados para API keys
        api_key_patterns = [
            # API Keys gerais
            (r'["\']?api[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{10,})["\']', "API Key"),
            (r'["\']?apikey["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{10,})["\']', "API Key"),
            (r'["\']?access[_-]?token["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_\.]{10,})["\']', "Access Token"),
            (r'["\']?secret[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{10,})["\']', "Secret Key"),
            (r'["\']?private[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{10,})["\']', "Private Key"),
            
            # Tokens específicos
            (r'Bearer\s+([A-Za-z0-9\-\._~\+\/]+)', "Bearer Token"),
            (r'["\']?token["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_\.]{15,})["\']', "Token"),
            
            # Serviços específicos
            (r'["\']?google[_-]?api[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{30,})["\']', "Google API Key"),
            (r'["\']?stripe[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{30,})["\']', "Stripe Key"),
            (r'["\']?aws[_-]?access[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9]{16,})["\']', "AWS Access Key"),
            (r'["\']?firebase[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{30,})["\']', "Firebase Key"),
            (r'["\']?openai[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{30,})["\']', "OpenAI Key"),
            (r'["\']?discord[_-]?token["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_\.]{50,})["\']', "Discord Token"),
            
            # Outros padrões
            (r'Authorization\s*:\s*["\']([^"\']+)["\']', "Authorization Header"),
            (r'X-API-Key\s*:\s*["\']([^"\']+)["\']', "X-API-Key Header"),
            (r'X-Auth-Token\s*:\s*["\']([^"\']+)["\']', "X-Auth-Token"),
            
            # Padrões específicos de formato
            (r'sk-[A-Za-z0-9]{48}', "OpenAI Secret Key"),
            (r'xoxb-[0-9]{11}-[0-9]{12}-[A-Za-z0-9]{24}', "Slack Bot Token"),
            (r'ghp_[A-Za-z0-9]{36}', "GitHub Personal Token"),
            (r'glpat-[A-Za-z0-9\-_]{20}', "GitLab Token"),
        ]
        
        # Buscar nos scripts JavaScript
        scripts = soup.find_all('script')
        all_js_content = ""
        for script in scripts:
            if script.string:
                all_js_content += script.string + "\n"
            if script.get('src'):
                try:
                    js_url = urljoin(base_url, script['src'])
                    js_response = self.session.get(js_url, timeout=10)
                    all_js_content += js_response.text + "\n"
                except:
                    pass
        
        # Combinar todo o conteúdo
        all_content = page_content + "\n" + all_js_content
        
        # Buscar patterns
        for pattern, key_type in api_key_patterns:
            matches = re.findall(pattern, all_content, re.IGNORECASE)
            for match in matches:
                if len(match) > 8 and match not in ['example', 'test', 'demo', 'placeholder', 'YOUR_API_KEY', 'API_KEY_HERE']:
                    api_keys.append({
                        'type': key_type,
                        'value': match,
                        'length': len(match),
                        'source': 'page_content'
                    })
        
        # Remover duplicatas
        unique_keys = []
        seen = set()
        for key in api_keys:
            if key['value'] not in seen:
                unique_keys.append(key)
                seen.add(key['value'])
        
        return unique_keys[:20]  # Limitar a 20 keys para performance

    def save_results(self, results, filename=None):
        """Salva os resultados em arquivo JSON"""
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            domain = urlparse(results["target_url"]).netloc.replace(".", "_")
            filename = f"api_analysis_{domain}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        return filename

# Função principal para uso no bot
def analyze_website_apis_comprehensive(url):
    """Função principal para análise completa de APIs"""
    analyzer = AdvancedAPIAnalyzer()
    return analyzer.comprehensive_api_discovery(url)

def analyze_website_apis_with_bypass(url):
    """Função avançada com bypass de captcha e extração de API keys"""
    analyzer = AdvancedAPIAnalyzer()
    return analyzer.comprehensive_analysis_with_bypass(url)

# Exemplo de uso
if __name__ == "__main__":
    url = input("Digite a URL do site para análise completa de APIs: ")
    
    print("🚀 Iniciando análise completa de APIs...")
    analyzer = AdvancedAPIAnalyzer()
    results = analyzer.comprehensive_api_discovery(url)
    
    if "error" in results:
        print(f"❌ Erro: {results['error']}")
    else:
        print("\n" + "="*80)
        print("📊 RELATÓRIO COMPLETO DE ANÁLISE DE APIs")
        print("="*80)
        
        print(f"\n🎯 Site analisado: {results['target_url']}")
        print(f"⏰ Análise realizada em: {results['analysis_timestamp']}")
        print(f"🔍 Total de endpoints descobertos: {results['total_endpoints_found']}")
        
        # Resumo por categoria
        categories = [
            ("📄 Formulários", "forms"),
            ("🔧 APIs JavaScript", "javascript_apis"),
            ("🌐 Endpoints testados", "endpoints"),
            ("📚 Documentação", "api_documentation"),
            ("📋 Swagger/OpenAPI", "swagger_openapi"),
            ("⚡ GraphQL", "graphql_endpoints"),
            ("🔌 WebSockets", "websocket_endpoints"),
            ("🔐 Autenticação", "authentication_methods"),
            ("🛡️ Vulnerabilidades", "common_vulnerabilities")
        ]
        
        for name, key in categories:
            data = results.get(key, [])
            if data:
                print(f"\n{name}: {len(data)} encontrado(s)")
                for item in data[:3]:  # Mostrar apenas os primeiros 3
                    if isinstance(item, dict):
                        if "url" in item:
                            print(f"  • {item['url']}")
                        elif "endpoint" in item:
                            print(f"  • {item['endpoint']}")
                        elif "action" in item:
                            print(f"  • {item['action']}")
        
        # Salvar resultados
        filename = analyzer.save_results(results)
        print(f"\n💾 Resultados salvos em: {filename}")
        
        print(f"\n✅ Análise concluída! Total de {results['total_endpoints_found']} endpoints descobertos.")
