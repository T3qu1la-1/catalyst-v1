
import requests
import os
import zipfile
import re
import time
from urllib.parse import urljoin, urlparse, unquote, quote
from bs4 import BeautifulSoup
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from datetime import datetime
import json
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import random

# Desabilitar warnings SSL
urllib3.disable_warnings(InsecureRequestWarning)

class AdvancedWebsiteCloner:
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
        
        self.downloaded_files = set()
        self.failed_downloads = []
        self.clone_directory = ""
        self.base_url = ""
        self.domain = ""
        self.total_files = 0
        self.downloaded_count = 0
        self.clone_stats = {
            'html_files': 0,
            'css_files': 0,
            'js_files': 0,
            'images': 0,
            'fonts': 0,
            'other_files': 0,
            'total_size': 0,
            'failed_downloads': 0,
            'scraped_urls': 0
        }

    def setup_session(self):
        """Configura a sessão com headers avançados para bypass de proteções"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0'
        ]
        
        self.session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-US;q=0.7,es;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Chromium";v="120", "Not(A:Brand";v="24", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })

    def clone_website(self, url, output_name=None, max_depth=3, include_external=True):
        """Clona um site de forma extremamente completa"""
        print(f"🚀 Iniciando clonagem AVANÇADA de: {url}")

        # Preparar diretórios
        parsed_url = urlparse(url)
        self.domain = parsed_url.netloc
        self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        if not output_name:
            output_name = self.domain.replace('.', '_').replace('-', '_')

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.clone_directory = f"cloned_sites/{output_name}_{timestamp}"

        # Criar estrutura completa de diretórios
        directories = [
            'assets', 'css', 'js', 'images', 'fonts', 'pages', 'data',
            'uploads', 'media', 'downloads', 'files', 'docs', 'api',
            'includes', 'components', 'modules', 'plugins', 'themes'
        ]
        
        os.makedirs(self.clone_directory, exist_ok=True)
        for dir_name in directories:
            os.makedirs(f"{self.clone_directory}/{dir_name}", exist_ok=True)

        try:
            # 1. Download da página principal com múltiplas tentativas
            print("📄 Baixando página principal...")
            main_html = self._download_html_advanced(url)
            if not main_html:
                return {"error": "Não foi possível baixar a página principal"}

            # 2. Análise profunda de recursos
            print("🔍 Executando análise PROFUNDA de recursos...")
            soup = BeautifulSoup(main_html, 'html.parser')
            
            # Extrair TODOS os recursos possíveis
            all_resources = set()
            
            # Recursos básicos
            basic_resources = self._extract_basic_resources(soup, url)
            all_resources.update(basic_resources)
            
            # Recursos do JavaScript inline
            js_resources = self._extract_js_resources(main_html, url)
            all_resources.update(js_resources)
            
            # Recursos do CSS inline
            css_resources = self._extract_css_resources(main_html, url)
            all_resources.update(css_resources)
            
            # Recursos de atributos data-*
            data_resources = self._extract_data_attributes(soup, url)
            all_resources.update(data_resources)
            
            # Recursos comuns por força bruta
            common_resources = self._discover_common_files(url)
            all_resources.update(common_resources)
            
            # Sitemap e robots.txt
            sitemap_resources = self._extract_from_sitemap(url)
            all_resources.update(sitemap_resources)

            print(f"📊 TOTAL DE RECURSOS DESCOBERTOS: {len(all_resources)}")

            # 3. Download paralelo com retry
            print(f"⬇️ Baixando {len(all_resources)} recursos...")
            self._download_resources_with_retry(list(all_resources))

            # 4. Buscar páginas internas recursivamente
            if max_depth > 1:
                print("🔗 Buscando páginas internas recursivamente...")
                internal_pages = self._find_internal_pages_recursive(soup, url, max_depth)
                
                for page_url in internal_pages:
                    print(f"📄 Processando página: {page_url}")
                    page_html = self._download_html_advanced(page_url)
                    if page_html:
                        # Salvar página
                        page_name = self._get_safe_filename(page_url, '.html')
                        page_path = f"{self.clone_directory}/pages/{page_name}"
                        
                        with open(page_path, 'w', encoding='utf-8') as f:
                            f.write(self._fix_html_paths(page_html, page_url))
                        
                        self.clone_stats['html_files'] += 1
                        
                        # Extrair recursos adicionais
                        page_soup = BeautifulSoup(page_html, 'html.parser')
                        page_resources = self._extract_all_page_resources(page_soup, page_url)
                        self._download_resources_with_retry(page_resources)

            # 5. Tentar extrair recursos de APIs conhecidas
            print("🔍 Buscando APIs e endpoints...")
            api_resources = self._discover_api_endpoints(url)
            if api_resources:
                self._download_resources_with_retry(api_resources)

            # 6. Processar e salvar HTML principal
            print("🔧 Processando HTML principal...")
            fixed_html = self._fix_html_paths_advanced(main_html, url)
            
            # Adicionar comentário indicando que é um site clonado
            clone_comment = f"""
<!-- 
    Site clonado pelo Catalyst Server - Website Cloner v2.0
    URL Original: {url}
    Data da clonagem: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    Total de recursos baixados: {len(all_resources)}
-->
"""
            
            # Inserir comentário após a tag <head> se existir
            if '<head>' in fixed_html:
                fixed_html = fixed_html.replace('<head>', f'<head>{clone_comment}')
            else:
                fixed_html = clone_comment + fixed_html
            
            with open(f"{self.clone_directory}/index.html", 'w', encoding='utf-8', errors='ignore') as f:
                f.write(fixed_html)

            # 7. Criar arquivos de configuração
            self._create_advanced_config(url)

            # 8. Criar arquivo .htaccess para funcionamento offline
            self._create_htaccess()

            # 9. Criar arquivo ZIP
            print("📦 Criando arquivo ZIP...")
            zip_path = self._create_zip_archive(output_name, timestamp)

            # 10. Gerar relatório detalhado
            report = self._generate_advanced_report(url, zip_path)

            print("✅ Clonagem AVANÇADA concluída com sucesso!")
            return report

        except Exception as e:
            print(f"❌ Erro na clonagem: {e}")
            return {"error": f"Erro na clonagem: {str(e)}"}

    def _download_html_advanced(self, url, retries=3):
        """Download avançado de HTML com múltiplas tentativas e bypass"""
        for attempt in range(retries):
            try:
                # Rotacionar User-Agent
                user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
                    'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/120.0'
                ]
                
                self.session.headers['User-Agent'] = random.choice(user_agents)
                # Garantir que o servidor saiba que aceitamos conteúdo comprimido
                self.session.headers['Accept-Encoding'] = 'gzip, deflate, br'
                
                # Adicionar delay aleatório
                if attempt > 0:
                    time.sleep(random.uniform(1, 3))
                
                print(f"📥 Tentativa {attempt + 1} - Baixando: {url}")
                response = self.session.get(url, timeout=30, allow_redirects=True, verify=False)
                response.raise_for_status()
                
                # Verificar encoding e decodificar automaticamente
                content = response.text
                
                # Verificar se o conteúdo foi decodificado corretamente
                if content and not content.startswith(('<!DOCTYPE', '<html', '<HTML')):
                    # Tentar diferentes encodings se o conteúdo não parecer HTML
                    for encoding in ['utf-8', 'iso-8859-1', 'windows-1252']:
                        try:
                            response.encoding = encoding
                            content = response.text
                            if content and (content.startswith(('<!DOCTYPE', '<html', '<HTML')) or 
                                          '<title>' in content.lower() or '<body>' in content.lower()):
                                break
                        except:
                            continue
                
                print(f"✅ HTML baixado: {len(content)} caracteres")
                
                # Verificar se o conteúdo é válido
                if len(content) < 100 or not any(tag in content.lower() for tag in ['<html', '<body', '<head', '<title']):
                    print(f"⚠️ Conteúdo pode estar corrompido ou não ser HTML válido")
                    if attempt < retries - 1:
                        continue
                
                return content
                
            except Exception as e:
                print(f"❌ Tentativa {attempt + 1} falhou: {e}")
                if attempt == retries - 1:
                    print(f"❌ Todas as tentativas falharam para: {url}")
                    return None

    def _extract_basic_resources(self, soup, base_url):
        """Extrai recursos básicos de forma mais abrangente"""
        resources = set()
        
        # CSS - Busca mais abrangente
        css_selectors = [
            'link[rel="stylesheet"]',
            'link[type="text/css"]',
            'link[rel="preload"][as="style"]',
            'style'
        ]
        
        for selector in css_selectors:
            elements = soup.select(selector)
            for element in elements:
                if element.name == 'link':
                    href = element.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        resources.add(full_url)
                elif element.name == 'style':
                    # CSS inline - extrair URLs
                    css_content = element.get_text()
                    css_urls = re.findall(r'url\([\'"]?([^\'")]+)[\'"]?\)', css_content)
                    for css_url in css_urls:
                        if not css_url.startswith('data:'):
                            full_url = urljoin(base_url, css_url)
                            resources.add(full_url)

        # JavaScript - Busca mais abrangente
        js_selectors = [
            'script[src]',
            'script[type="module"]',
            'script[type="importmap"]'
        ]
        
        for selector in js_selectors:
            elements = soup.select(selector)
            for element in elements:
                src = element.get('src')
                if src:
                    full_url = urljoin(base_url, src)
                    resources.add(full_url)

        # Imagens - Todos os tipos possíveis
        img_selectors = [
            'img[src]', 'img[data-src]', 'img[data-lazy]', 'img[data-original]',
            'picture source[srcset]', 'picture source[data-srcset]',
            '[style*="background-image"]', '[data-background]',
            'svg image[href]'
        ]
        
        for selector in img_selectors:
            elements = soup.select(selector)
            for element in elements:
                # Múltiplos atributos possíveis
                src_attrs = ['src', 'data-src', 'data-lazy', 'data-original', 'href']
                
                # Verificar xlink:href separadamente
                xlink_href = element.get('xlink:href') or element.get('{http://www.w3.org/1999/xlink}href')
                if xlink_href and not xlink_href.startswith('data:'):
                    full_url = urljoin(base_url, xlink_href)
                    resources.add(full_url)
                
                for attr in src_attrs:
                    src = element.get(attr)
                    if src and not src.startswith('data:'):
                        # Processar srcset se houver
                        if 'srcset' in attr or attr == 'srcset':
                            urls = re.findall(r'([^\s,]+)', src)
                            for url in urls:
                                if not url.startswith(('http', 'data:')):
                                    full_url = urljoin(base_url, url)
                                    resources.add(full_url)
                        else:
                            full_url = urljoin(base_url, src)
                            resources.add(full_url)

                # Background images no style
                style = element.get('style', '')
                if 'background-image' in style:
                    bg_urls = re.findall(r'background-image:\s*url\([\'"]?([^\'")]+)[\'"]?\)', style)
                    for bg_url in bg_urls:
                        if not bg_url.startswith('data:'):
                            full_url = urljoin(base_url, bg_url)
                            resources.add(full_url)

        # Vídeos e áudios
        media_selectors = [
            'video[src]', 'video source[src]', 'video[poster]',
            'audio[src]', 'audio source[src]',
            'embed[src]', 'object[data]', 'iframe[src]'
        ]
        
        for selector in media_selectors:
            elements = soup.select(selector)
            for element in elements:
                src_attrs = ['src', 'data', 'poster']
                for attr in src_attrs:
                    src = element.get(attr)
                    if src and not src.startswith(('data:', 'javascript:', 'mailto:')):
                        full_url = urljoin(base_url, src)
                        resources.add(full_url)

        # Fonts e ícones
        font_selectors = [
            'link[rel="preload"][as="font"]',
            'link[rel="icon"]', 'link[rel="shortcut icon"]',
            'link[rel="apple-touch-icon"]', 'link[rel="mask-icon"]'
        ]
        
        for selector in font_selectors:
            elements = soup.select(selector)
            for element in elements:
                href = element.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    resources.add(full_url)

        return list(resources)

    def _extract_js_resources(self, html_content, base_url):
        """Extrai recursos do JavaScript inline"""
        resources = set()
        
        # Padrões para URLs em JavaScript
        js_patterns = [
            r'["\']([^"\']+\.(?:js|css|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot))["\']',
            r'src\s*[:=]\s*["\']([^"\']+)["\']',
            r'href\s*[:=]\s*["\']([^"\']+)["\']',
            r'url\s*[:=]\s*["\']([^"\']+)["\']',
            r'ajax\(["\']([^"\']+)["\']',
            r'fetch\(["\']([^"\']+)["\']',
            r'XMLHttpRequest.*["\']([^"\']+)["\']'
        ]
        
        for pattern in js_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if not match.startswith(('data:', 'javascript:', 'mailto:', '#')):
                    full_url = urljoin(base_url, match)
                    resources.add(full_url)
        
        return list(resources)

    def _extract_css_resources(self, html_content, base_url):
        """Extrai recursos do CSS inline"""
        resources = set()
        
        # Extrair CSS entre tags <style>
        css_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html_content, re.DOTALL | re.IGNORECASE)
        
        for css_block in css_blocks:
            # URLs em CSS
            urls = re.findall(r'url\([\'"]?([^\'")]+)[\'"]?\)', css_block)
            for url in urls:
                if not url.startswith('data:'):
                    full_url = urljoin(base_url, url)
                    resources.add(full_url)
        
        return list(resources)

    def _extract_data_attributes(self, soup, base_url):
        """Extrai recursos de atributos data-*"""
        resources = set()
        
        # Buscar todos os elementos com atributos data-*
        all_elements = soup.find_all()
        
        for element in all_elements:
            for attr_name, attr_value in element.attrs.items():
                if attr_name.startswith('data-') and isinstance(attr_value, str):
                    # Verificar se parece com uma URL
                    if any(ext in attr_value.lower() for ext in ['.js', '.css', '.png', '.jpg', '.gif', '.svg', '.woff', '.pdf']):
                        if not attr_value.startswith(('data:', 'javascript:', 'mailto:')):
                            full_url = urljoin(base_url, attr_value)
                            resources.add(full_url)
        
        return list(resources)

    def _discover_common_files(self, base_url):
        """Descobre arquivos comuns por força bruta"""
        resources = set()
        
        common_paths = [
            # CSS
            '/css/style.css', '/css/main.css', '/css/app.css', '/css/bootstrap.css',
            '/css/custom.css', '/css/theme.css', '/css/responsive.css',
            '/assets/css/style.css', '/assets/css/main.css',
            '/static/css/style.css', '/static/css/main.css',
            
            # JavaScript
            '/js/main.js', '/js/app.js', '/js/script.js', '/js/custom.js',
            '/js/jquery.js', '/js/bootstrap.js', '/js/plugins.js',
            '/assets/js/main.js', '/assets/js/app.js',
            '/static/js/main.js', '/static/js/app.js',
            
            # Imagens
            '/images/logo.png', '/images/logo.jpg', '/images/logo.svg',
            '/img/logo.png', '/img/logo.jpg', '/img/logo.svg',
            '/assets/images/logo.png', '/assets/img/logo.png',
            '/static/images/logo.png', '/static/img/logo.png',
            
            # Ícones
            '/favicon.ico', '/favicon.png', '/apple-touch-icon.png',
            '/icon-192x192.png', '/icon-512x512.png',
            
            # Arquivos de configuração
            '/robots.txt', '/sitemap.xml', '/sitemap.txt',
            '/manifest.json', '/.well-known/security.txt',
            
            # Uploads e media
            '/uploads/', '/media/', '/files/', '/documents/', '/downloads/'
        ]
        
        print(f"🔍 Testando {len(common_paths)} caminhos comuns...")
        
        for path in common_paths:
            try:
                test_url = urljoin(base_url, path)
                response = self.session.head(test_url, timeout=5, verify=False)
                if response.status_code == 200:
                    resources.add(test_url)
                    print(f"  ✅ Encontrado: {path}")
            except:
                continue
        
        return list(resources)

    def _extract_from_sitemap(self, base_url):
        """Extrai URLs do sitemap.xml"""
        resources = set()
        
        sitemap_urls = [
            '/sitemap.xml',
            '/sitemap.txt',
            '/sitemap_index.xml',
            '/sitemaps.xml'
        ]
        
        for sitemap_path in sitemap_urls:
            try:
                sitemap_url = urljoin(base_url, sitemap_path)
                response = self.session.get(sitemap_url, timeout=10, verify=False)
                if response.status_code == 200:
                    print(f"📄 Processando sitemap: {sitemap_path}")
                    
                    # XML sitemap
                    if sitemap_path.endswith('.xml'):
                        urls = re.findall(r'<loc>(.*?)</loc>', response.text)
                        resources.update(urls)
                    
                    # TXT sitemap
                    elif sitemap_path.endswith('.txt'):
                        lines = response.text.strip().split('\n')
                        for line in lines:
                            if line.strip() and line.startswith('http'):
                                resources.add(line.strip())
                                
            except:
                continue
                
        return list(resources)

    def _discover_api_endpoints(self, base_url):
        """Tenta descobrir endpoints de API"""
        resources = set()
        
        api_paths = [
            '/api/', '/api/v1/', '/api/v2/', '/v1/', '/v2/',
            '/graphql', '/graphql/', '/rest/', '/rest/v1/',
            '/wp-json/', '/wp-json/wp/v2/',
            '/.well-known/', '/health', '/status'
        ]
        
        for api_path in api_paths:
            try:
                api_url = urljoin(base_url, api_path)
                response = self.session.get(api_url, timeout=5, verify=False)
                if response.status_code == 200:
                    resources.add(api_url)
                    print(f"  🔌 API encontrada: {api_path}")
            except:
                continue
                
        return list(resources)

    def _find_internal_pages_recursive(self, soup, base_url, max_depth, current_depth=1):
        """Encontra páginas internas recursivamente"""
        if current_depth >= max_depth:
            return []
            
        internal_pages = set()
        domain = urlparse(base_url).netloc

        # Buscar todos os links
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)

                # Verificar se é página interna
                if (parsed.netloc == domain and 
                    not parsed.fragment and 
                    not full_url.endswith(('.pdf', '.zip', '.exe', '.jpg', '.png', '.gif', '.css', '.js'))):
                    internal_pages.add(full_url)

        # Limitar número de páginas para evitar sobrecarga
        internal_pages = list(internal_pages)[:50]
        
        # Buscar recursivamente em algumas páginas
        if current_depth < max_depth:
            for page_url in internal_pages[:10]:  # Processar apenas as primeiras 10
                try:
                    page_html = self._download_html_advanced(page_url)
                    if page_html:
                        page_soup = BeautifulSoup(page_html, 'html.parser')
                        deeper_pages = self._find_internal_pages_recursive(
                            page_soup, page_url, max_depth, current_depth + 1
                        )
                        internal_pages.extend(deeper_pages)
                except:
                    continue

        return list(set(internal_pages))

    def _extract_all_page_resources(self, soup, base_url):
        """Extrai todos os recursos de uma página"""
        resources = set()
        
        # Combinar todos os métodos de extração
        resources.update(self._extract_basic_resources(soup, base_url))
        
        page_html = str(soup)
        resources.update(self._extract_js_resources(page_html, base_url))
        resources.update(self._extract_css_resources(page_html, base_url))
        resources.update(self._extract_data_attributes(soup, base_url))
        
        return list(resources)

    def _download_resources_with_retry(self, resources):
        """Download de recursos com retry e controle de erro"""
        unique_resources = list(set(resources))
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_resource = {
                executor.submit(self._download_single_resource, resource): resource 
                for resource in unique_resources
            }

            for future in as_completed(future_to_resource):
                resource = future_to_resource[future]
                try:
                    result = future.result()
                    if result:
                        self.downloaded_count += 1
                        if self.downloaded_count % 10 == 0:
                            print(f"✅ [{self.downloaded_count}/{len(unique_resources)}] recursos baixados...")
                    else:
                        self.failed_downloads.append(resource)
                        self.clone_stats['failed_downloads'] += 1
                except Exception as e:
                    print(f"❌ Erro ao baixar {resource}: {e}")
                    self.failed_downloads.append(resource)
                    self.clone_stats['failed_downloads'] += 1

    def _download_single_resource(self, url, retries=3):
        """Download de um único recurso com retry"""
        if url in self.downloaded_files:
            return True

        for attempt in range(retries):
            try:
                # Delay entre tentativas
                if attempt > 0:
                    time.sleep(random.uniform(0.5, 1.5))

                # Headers específicos para diferentes tipos de arquivo
                headers = self.session.headers.copy()
                if url.endswith(('.css', '.js')):
                    headers['Accept'] = 'text/css,*/*;q=0.1' if url.endswith('.css') else 'application/javascript,*/*;q=0.1'
                elif url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
                    headers['Accept'] = 'image/webp,image/apng,image/*,*/*;q=0.8'

                response = self.session.get(url, timeout=15, stream=True, verify=False, headers=headers)
                response.raise_for_status()

                # Determinar nome e pasta do arquivo
                filename = self._get_safe_filename(url)
                
                # Determinar tipo e pasta baseado na extensão e content-type
                content_type = response.headers.get('Content-Type', '').lower()
                file_extension = os.path.splitext(filename)[1].lower()
                
                if file_extension in ['.css'] or 'css' in content_type:
                    filepath = f"{self.clone_directory}/css/{filename}"
                    self.clone_stats['css_files'] += 1
                elif file_extension in ['.js'] or 'javascript' in content_type:
                    filepath = f"{self.clone_directory}/js/{filename}"
                    self.clone_stats['js_files'] += 1
                elif file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp'] or 'image' in content_type:
                    filepath = f"{self.clone_directory}/images/{filename}"
                    self.clone_stats['images'] += 1
                elif file_extension in ['.woff', '.woff2', '.ttf', '.otf', '.eot'] or 'font' in content_type:
                    filepath = f"{self.clone_directory}/fonts/{filename}"
                    self.clone_stats['fonts'] += 1
                elif file_extension in ['.mp4', '.webm', '.ogg', '.mp3', '.wav'] or any(x in content_type for x in ['video', 'audio']):
                    filepath = f"{self.clone_directory}/media/{filename}"
                    self.clone_stats['other_files'] += 1
                elif file_extension in ['.pdf', '.doc', '.docx', '.txt']:
                    filepath = f"{self.clone_directory}/docs/{filename}"
                    self.clone_stats['other_files'] += 1
                else:
                    filepath = f"{self.clone_directory}/assets/{filename}"
                    self.clone_stats['other_files'] += 1

                # Criar diretório se necessário
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                # Baixar arquivo
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                file_size = os.path.getsize(filepath)
                self.clone_stats['total_size'] += file_size
                self.downloaded_files.add(url)

                # Se for CSS, processar recursos internos
                if file_extension == '.css':
                    self._process_css_file(filepath, url)

                return True

            except Exception as e:
                if attempt == retries - 1:
                    print(f"❌ Falha final ao baixar {url}: {e}")
                    return False

        return False

    def _process_css_file(self, css_filepath, css_url):
        """Processa arquivo CSS para extrair e baixar recursos internos"""
        try:
            # Tentar diferentes encodings para ler o CSS
            css_content = None
            for encoding in ['utf-8', 'iso-8859-1', 'windows-1252']:
                try:
                    with open(css_filepath, 'r', encoding=encoding, errors='ignore') as f:
                        css_content = f.read()
                    break
                except:
                    continue
            
            if not css_content:
                print(f"⚠️ Não foi possível ler o arquivo CSS: {css_filepath}")
                return

            # Extrair URLs do CSS
            url_pattern = r'url\([\'"]?([^\'")]+)[\'"]?\)'
            urls = re.findall(url_pattern, css_content)

            css_resources = []
            for url in urls:
                if not url.startswith(('data:', 'http')):
                    full_url = urljoin(css_url, url)
                    css_resources.append(full_url)

            # Baixar recursos do CSS
            if css_resources:
                self._download_resources_with_retry(css_resources)

            # Atualizar caminhos no CSS
            updated_css = self._fix_css_paths_advanced(css_content, css_url)
            
            # Salvar com encoding UTF-8
            with open(css_filepath, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(updated_css)

        except Exception as e:
            print(f"❌ Erro ao processar CSS {css_filepath}: {e}")

    def _fix_html_paths_advanced(self, html_content, base_url):
        """Corrige caminhos no HTML de forma avançada"""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Mapeamento de correções
        path_mappings = {
            'css': 'css/',
            'js': 'js/',
            'images': 'images/',
            'fonts': 'fonts/',
            'media': 'media/',
            'docs': 'docs/',
            'assets': 'assets/'
        }

        # Corrigir links CSS
        for link in soup.find_all('link'):
            href = link.get('href')
            if href and not href.startswith(('data:', 'javascript:', '#')):
                filename = self._get_safe_filename(urljoin(base_url, href))
                file_ext = os.path.splitext(filename)[1].lower()
                
                if file_ext == '.css' or link.get('rel') == ['stylesheet']:
                    link['href'] = f'css/{filename}'
                elif file_ext in ['.ico', '.png', '.jpg']:
                    link['href'] = f'images/{filename}'

        # Corrigir scripts
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if src and not src.startswith(('data:', 'javascript:')):
                filename = self._get_safe_filename(urljoin(base_url, src))
                script['src'] = f'js/{filename}'

        # Corrigir imagens
        for img in soup.find_all('img'):
            for attr in ['src', 'data-src', 'data-lazy']:
                src = img.get(attr)
                if src and not src.startswith(('data:', 'javascript:')):
                    filename = self._get_safe_filename(urljoin(base_url, src))
                    img[attr] = f'images/{filename}'

        # Corrigir vídeos e áudios
        for media in soup.find_all(['video', 'audio', 'source']):
            src = media.get('src')
            if src and not src.startswith(('data:', 'javascript:')):
                filename = self._get_safe_filename(urljoin(base_url, src))
                media['src'] = f'media/{filename}'

        return str(soup)

    def _fix_css_paths_advanced(self, css_content, css_url):
        """Corrige caminhos em arquivos CSS de forma avançada"""
        def replace_url(match):
            url = match.group(1)
            if not url.startswith(('data:', 'http')):
                full_url = urljoin(css_url, url)
                filename = self._get_safe_filename(full_url)
                file_ext = os.path.splitext(filename)[1].lower()
                
                if file_ext in ['.woff', '.woff2', '.ttf', '.otf', '.eot']:
                    return f'url(../fonts/{filename})'
                elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
                    return f'url(../images/{filename})'
                else:
                    return f'url(../assets/{filename})'
            return match.group(0)

        return re.sub(r'url\([\'"]?([^\'")]+)[\'"]?\)', replace_url, css_content)

    def _get_safe_filename(self, url, default_ext=''):
        """Gera nome de arquivo seguro e único"""
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)

        if not filename or '.' not in filename:
            # Usar hash da URL se não houver nome de arquivo
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            
            # Tentar determinar extensão
            if default_ext:
                ext = default_ext
            else:
                # Detectar por content-type ou URL
                if '.css' in url:
                    ext = '.css'
                elif '.js' in url:
                    ext = '.js'
                elif any(x in url for x in ['.png', '.jpg', '.jpeg', '.gif']):
                    ext = '.png'
                else:
                    ext = '.html'
            
            filename = f"file_{url_hash}{ext}"

        # Limpar caracteres inválidos
        filename = re.sub(r'[^\w\-_\.]', '_', filename)
        
        # Evitar nomes muito longos
        if len(filename) > 100:
            name, ext = os.path.splitext(filename)
            filename = name[:90] + ext

        return filename

    def _create_advanced_config(self, original_url):
        """Cria arquivo de configuração avançado"""
        config = {
            'clone_info': {
                'original_url': original_url,
                'clone_date': datetime.now().isoformat(),
                'domain': self.domain,
                'cloner_version': '2.0_advanced'
            },
            'statistics': self.clone_stats,
            'failed_downloads': self.failed_downloads,
            'downloaded_count': self.downloaded_count,
            'instructions': {
                'pt': 'Abra index.html no navegador para visualizar o site clonado',
                'en': 'Open index.html in browser to view the cloned website'
            },
            'notes': [
                'Este clone foi criado com o sistema avançado',
                'Todos os recursos possíveis foram extraídos',
                'Caminhos foram corrigidos para uso offline'
            ]
        }

        with open(f"{self.clone_directory}/clone_info.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _create_htaccess(self):
        """Cria arquivo .htaccess para melhor funcionamento"""
        htaccess_content = """# Arquivo gerado pelo Advanced Website Cloner
DirectoryIndex index.html index.htm

# Permitir acesso a todos os arquivos
<Files "*">
    Order allow,deny
    Allow from all
</Files>

# Definir tipos MIME
AddType text/css .css
AddType application/javascript .js
AddType image/png .png
AddType image/jpeg .jpg .jpeg
AddType image/gif .gif
AddType image/svg+xml .svg

# Cache
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType text/css "access plus 1 year"
    ExpiresByType application/javascript "access plus 1 year"
    ExpiresByType image/png "access plus 1 year"
    ExpiresByType image/jpg "access plus 1 year"
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType image/gif "access plus 1 year"
</IfModule>
"""
        
        with open(f"{self.clone_directory}/.htaccess", 'w', encoding='utf-8') as f:
            f.write(htaccess_content)

    def _create_zip_archive(self, output_name, timestamp):
        """Cria arquivo ZIP temporário (será deletado após envio)"""
        # Criar ZIP temporário que será deletado após uso
        zip_filename = f"{output_name}_COMPLETE_{timestamp}.zip"
        zip_path = f"temp/{zip_filename}"
        
        # Garantir que o diretório temp existe
        os.makedirs("temp", exist_ok=True)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            for root, dirs, files in os.walk(self.clone_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.clone_directory)
                    zipf.write(file_path, arcname)

        # Remover diretório temporário
        import shutil
        shutil.rmtree(self.clone_directory)

        return zip_path

    def _generate_advanced_report(self, original_url, zip_path):
        """Gera relatório avançado da clonagem"""
        total_size_mb = self.clone_stats['total_size'] / (1024 * 1024)
        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)

        return {
            'success': True,
            'original_url': original_url,
            'zip_file': zip_path,
            'zip_size_mb': round(zip_size_mb, 2),
            'statistics': {
                'html_files': self.clone_stats['html_files'],
                'css_files': self.clone_stats['css_files'],
                'js_files': self.clone_stats['js_files'],
                'images': self.clone_stats['images'],
                'fonts': self.clone_stats['fonts'],
                'other_files': self.clone_stats['other_files'],
                'total_files': sum([
                    self.clone_stats['html_files'],
                    self.clone_stats['css_files'],
                    self.clone_stats['js_files'],
                    self.clone_stats['images'],
                    self.clone_stats['fonts'],
                    self.clone_stats['other_files']
                ]),
                'total_size_mb': round(total_size_mb, 2),
                'failed_downloads': self.clone_stats['failed_downloads'],
                'success_rate': round((self.downloaded_count / (self.downloaded_count + self.clone_stats['failed_downloads'])) * 100, 2) if (self.downloaded_count + self.clone_stats['failed_downloads']) > 0 else 100
            },
            'failed_urls': self.failed_downloads[:20] if self.failed_downloads else [],
            'cloner_version': '2.0_advanced'
        }

def clone_website_professional(url, output_name=None, max_depth=3):
    """Função principal para clonagem avançada de sites"""
    cloner = AdvancedWebsiteCloner()
    return cloner.clone_website(url, output_name, max_depth)

# Exemplo de uso
if __name__ == "__main__":
    url = input("Digite a URL do site para clonar: ")
    
    print("🚀 Iniciando clonagem AVANÇADA...")
    cloner = AdvancedWebsiteCloner()
    result = cloner.clone_website(url, max_depth=2)

    if result.get('success'):
        print("\n" + "="*80)
        print("✅ CLONAGEM AVANÇADA CONCLUÍDA COM SUCESSO!")
        print("="*80)
        print(f"🌐 Site original: {result['original_url']}")
        print(f"📁 Arquivo ZIP: {result['zip_file']}")
        print(f"📊 Tamanho: {result['zip_size_mb']} MB")
        
        stats = result['statistics']
        print(f"📄 Arquivos HTML: {stats['html_files']}")
        print(f"🎨 Arquivos CSS: {stats['css_files']}")
        print(f"⚡ Arquivos JS: {stats['js_files']}")
        print(f"🖼️ Imagens: {stats['images']}")
        print(f"🔤 Fontes: {stats['fonts']}")
        print(f"📁 Outros: {stats['other_files']}")
        print(f"📈 Total de arquivos: {stats['total_files']}")
        print(f"💾 Tamanho total: {stats['total_size_mb']} MB")
        print(f"❌ Falhas: {stats['failed_downloads']}")
        print(f"✅ Taxa de sucesso: {stats['success_rate']}%")
        
        # Mostrar algumas URLs que falharam
        if result.get('failed_urls'):
            print(f"\n⚠️ Primeiras URLs que falharam:")
            for i, failed_url in enumerate(result['failed_urls'][:5]):
                print(f"  {i+1}. {failed_url}")
            if len(result['failed_urls']) > 5:
                print(f"  ... e mais {len(result['failed_urls']) - 5} URLs")
                
        print(f"\n🌐 Extraia o arquivo e abra index.html no navegador!")
    else:
        print(f"❌ Erro: {result.get('error')}")
