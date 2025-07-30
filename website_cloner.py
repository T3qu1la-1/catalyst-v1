
import requests
import os
import zipfile
import re
import time
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from datetime import datetime
import json

class ProfessionalWebsiteCloner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-US;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1'
        })

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
            'failed_downloads': 0
        }

    def clone_website(self, url, output_name=None, max_depth=2, include_external=False):
        """Clona um site completamente"""
        print(f"🚀 Iniciando clonagem profissional de: {url}")

        # Preparar diretórios
        parsed_url = urlparse(url)
        self.domain = parsed_url.netloc
        self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        if not output_name:
            output_name = self.domain.replace('.', '_')

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.clone_directory = f"cloned_sites/{output_name}_{timestamp}"

        # Criar estrutura de diretórios
        os.makedirs(self.clone_directory, exist_ok=True)
        os.makedirs(f"{self.clone_directory}/assets", exist_ok=True)
        os.makedirs(f"{self.clone_directory}/css", exist_ok=True)
        os.makedirs(f"{self.clone_directory}/js", exist_ok=True)
        os.makedirs(f"{self.clone_directory}/images", exist_ok=True)
        os.makedirs(f"{self.clone_directory}/fonts", exist_ok=True)
        os.makedirs(f"{self.clone_directory}/pages", exist_ok=True)

        try:
            # 1. Baixar página principal
            print("📄 Baixando página principal...")
            main_html = self._download_html(url)
            if not main_html:
                return {"error": "Não foi possível baixar a página principal"}

            # 2. Analisar e extrair recursos
            print("🔍 Analisando recursos da página...")
            soup = BeautifulSoup(main_html, 'html.parser')
            resources = self._extract_all_resources(soup, url)

            # 3. Baixar todos os recursos em paralelo
            print(f"⬇️ Baixando {len(resources)} recursos...")
            self._download_resources_parallel(resources)

            # 4. Se depth > 1, buscar páginas internas
            if max_depth > 1:
                print("🔗 Buscando páginas internas...")
                internal_pages = self._find_internal_pages(soup, url, max_depth)
                for page_url in internal_pages:
                    page_html = self._download_html(page_url)
                    if page_html:
                        page_name = self._get_safe_filename(page_url)
                        with open(f"{self.clone_directory}/pages/{page_name}.html", 'w', encoding='utf-8') as f:
                            f.write(self._fix_html_paths(page_html, page_url))

                        # Extrair recursos adicionais das páginas internas
                        page_soup = BeautifulSoup(page_html, 'html.parser')
                        page_resources = self._extract_all_resources(page_soup, page_url)
                        self._download_resources_parallel(page_resources)

            # 5. Processar e salvar HTML principal com caminhos corrigidos
            print("🔧 Processando HTML principal...")
            fixed_html = self._fix_html_paths(main_html, url)
            with open(f"{self.clone_directory}/index.html", 'w', encoding='utf-8') as f:
                f.write(fixed_html)

            # 6. Criar arquivo de configuração
            self._create_config_file(url)

            # 7. Criar arquivo ZIP
            print("📦 Criando arquivo ZIP...")
            zip_path = self._create_zip_archive(output_name, timestamp)

            # 8. Gerar relatório
            report = self._generate_report(url, zip_path)

            print("✅ Clonagem concluída com sucesso!")
            return report

        except Exception as e:
            return {"error": f"Erro na clonagem: {str(e)}"}

    def _download_html(self, url):
        """Baixa o HTML de uma página"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"❌ Erro ao baixar HTML de {url}: {e}")
            return None

    def _extract_all_resources(self, soup, base_url):
        """Extrai todos os recursos da página"""
        resources = []

        # CSS files
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                resources.append({
                    'url': full_url,
                    'type': 'css',
                    'element': link
                })

        # JavaScript files
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if src:
                full_url = urljoin(base_url, src)
                resources.append({
                    'url': full_url,
                    'type': 'js',
                    'element': script
                })

        # Images
        for img in soup.find_all('img', src=True):
            src = img.get('src')
            if src:
                full_url = urljoin(base_url, src)
                resources.append({
                    'url': full_url,
                    'type': 'image',
                    'element': img
                })

        # Background images em CSS inline
        for element in soup.find_all(style=True):
            style = element.get('style', '')
            bg_matches = re.findall(r'background-image:\s*url\([\'"]?([^\'")]+)[\'"]?\)', style)
            for bg_url in bg_matches:
                full_url = urljoin(base_url, bg_url)
                resources.append({
                    'url': full_url,
                    'type': 'image',
                    'element': element
                })

        # Fontes
        for link in soup.find_all('link'):
            href = link.get('href', '')
            if any(font_ext in href.lower() for font_ext in ['.woff', '.woff2', '.ttf', '.otf', '.eot']):
                full_url = urljoin(base_url, href)
                resources.append({
                    'url': full_url,
                    'type': 'font',
                    'element': link
                })

        # Favicon
        for link in soup.find_all('link', rel=['icon', 'shortcut icon', 'apple-touch-icon']):
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                resources.append({
                    'url': full_url,
                    'type': 'image',
                    'element': link
                })

        # Videos e audios
        for media in soup.find_all(['video', 'audio']):
            src = media.get('src')
            if src:
                full_url = urljoin(base_url, src)
                resources.append({
                    'url': full_url,
                    'type': 'media',
                    'element': media
                })

            # Sources dentro de video/audio
            for source in media.find_all('source'):
                src = source.get('src')
                if src:
                    full_url = urljoin(base_url, src)
                    resources.append({
                        'url': full_url,
                        'type': 'media',
                        'element': source
                    })

        return resources

    def _download_resources_parallel(self, resources):
        """Baixa recursos em paralelo"""
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_resource = {
                executor.submit(self._download_resource, resource): resource 
                for resource in resources
            }

            for future in as_completed(future_to_resource):
                resource = future_to_resource[future]
                try:
                    result = future.result()
                    if result:
                        self.downloaded_count += 1
                        print(f"✅ [{self.downloaded_count}/{len(resources)}] {resource['url']}")
                    else:
                        self.failed_downloads.append(resource['url'])
                        self.clone_stats['failed_downloads'] += 1
                except Exception as e:
                    print(f"❌ Erro ao baixar {resource['url']}: {e}")
                    self.failed_downloads.append(resource['url'])
                    self.clone_stats['failed_downloads'] += 1

    def _download_resource(self, resource):
        """Baixa um recurso específico"""
        url = resource['url']
        resource_type = resource['type']

        if url in self.downloaded_files:
            return True

        try:
            response = self.session.get(url, timeout=15, stream=True)
            response.raise_for_status()

            # Determinar nome e pasta do arquivo
            filename = self._get_safe_filename(url)

            if resource_type == 'css':
                filepath = f"{self.clone_directory}/css/{filename}"
                self.clone_stats['css_files'] += 1
            elif resource_type == 'js':
                filepath = f"{self.clone_directory}/js/{filename}"
                self.clone_stats['js_files'] += 1
            elif resource_type == 'image':
                filepath = f"{self.clone_directory}/images/{filename}"
                self.clone_stats['images'] += 1
            elif resource_type == 'font':
                filepath = f"{self.clone_directory}/fonts/{filename}"
                self.clone_stats['fonts'] += 1
            else:
                filepath = f"{self.clone_directory}/assets/{filename}"
                self.clone_stats['other_files'] += 1

            # Baixar arquivo
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            self.clone_stats['total_size'] += os.path.getsize(filepath)
            self.downloaded_files.add(url)

            # Se for CSS, baixar recursos do CSS também
            if resource_type == 'css':
                self._download_css_resources(filepath, url)

            return True

        except Exception as e:
            print(f"❌ Falha ao baixar {url}: {e}")
            return False

    def _download_css_resources(self, css_filepath, css_url):
        """Baixa recursos referenciados em arquivos CSS"""
        try:
            with open(css_filepath, 'r', encoding='utf-8', errors='ignore') as f:
                css_content = f.read()

            # Buscar URLs em CSS
            url_pattern = r'url\([\'"]?([^\'")]+)[\'"]?\)'
            urls = re.findall(url_pattern, css_content)

            for url in urls:
                if not url.startswith(('data:', 'http')):
                    full_url = urljoin(css_url, url)
                    resource = {
                        'url': full_url,
                        'type': 'font' if any(ext in url.lower() for ext in ['.woff', '.woff2', '.ttf', '.otf']) else 'image',
                        'element': None
                    }
                    self._download_resource(resource)

            # Atualizar caminhos no CSS
            updated_css = self._fix_css_paths(css_content, css_url)
            with open(css_filepath, 'w', encoding='utf-8') as f:
                f.write(updated_css)

        except Exception as e:
            print(f"❌ Erro ao processar CSS {css_filepath}: {e}")

    def _fix_html_paths(self, html_content, base_url):
        """Corrige caminhos no HTML para arquivos locais"""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Corrigir links CSS
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                filename = self._get_safe_filename(urljoin(base_url, href))
                link['href'] = f'css/{filename}'

        # Corrigir scripts
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if src:
                filename = self._get_safe_filename(urljoin(base_url, src))
                script['src'] = f'js/{filename}'

        # Corrigir imagens
        for img in soup.find_all('img', src=True):
            src = img.get('src')
            if src:
                filename = self._get_safe_filename(urljoin(base_url, src))
                img['src'] = f'images/{filename}'

        # Corrigir favicons
        for link in soup.find_all('link', rel=['icon', 'shortcut icon']):
            href = link.get('href')
            if href:
                filename = self._get_safe_filename(urljoin(base_url, href))
                link['href'] = f'images/{filename}'

        return str(soup)

    def _fix_css_paths(self, css_content, css_url):
        """Corrige caminhos em arquivos CSS"""
        def replace_url(match):
            url = match.group(1)
            if not url.startswith(('data:', 'http')):
                full_url = urljoin(css_url, url)
                filename = self._get_safe_filename(full_url)
                if any(ext in url.lower() for ext in ['.woff', '.woff2', '.ttf', '.otf']):
                    return f'url(../fonts/{filename})'
                else:
                    return f'url(../images/{filename})'
            return match.group(0)

        return re.sub(r'url\([\'"]?([^\'")]+)[\'"]?\)', replace_url, css_content)

    def _find_internal_pages(self, soup, base_url, max_depth):
        """Encontra páginas internas do site"""
        internal_pages = set()
        domain = urlparse(base_url).netloc

        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)

                # Verificar se é página interna
                if (parsed.netloc == domain and 
                    not parsed.fragment and 
                    not full_url.endswith(('.pdf', '.zip', '.exe', '.jpg', '.png', '.gif'))):
                    internal_pages.add(full_url)

                if len(internal_pages) >= 20:  # Limitar a 20 páginas
                    break

        return list(internal_pages)

    def _get_safe_filename(self, url):
        """Gera nome de arquivo seguro a partir da URL"""
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)

        if not filename or '.' not in filename:
            # Usar hash da URL se não houver nome de arquivo
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

            # Tentar determinar extensão pelo Content-Type
            try:
                response = self.session.head(url, timeout=5)
                content_type = response.headers.get('Content-Type', '')
                ext = mimetypes.guess_extension(content_type.split(';')[0]) or '.html'
                filename = f"file_{url_hash}{ext}"
            except:
                filename = f"file_{url_hash}.html"

        # Limpar caracteres inválidos
        filename = re.sub(r'[^\w\-_\.]', '_', filename)
        return filename

    def _create_config_file(self, original_url):
        """Cria arquivo de configuração com informações da clonagem"""
        config = {
            'original_url': original_url,
            'clone_date': datetime.now().isoformat(),
            'domain': self.domain,
            'stats': self.clone_stats,
            'failed_downloads': self.failed_downloads,
            'instructions': {
                'pt': 'Abra index.html no navegador para visualizar o site clonado',
                'en': 'Open index.html in browser to view the cloned website'
            }
        }

        with open(f"{self.clone_directory}/clone_info.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _create_zip_archive(self, output_name, timestamp):
        """Cria arquivo ZIP com todo o site clonado"""
        zip_filename = f"{output_name}_{timestamp}.zip"
        zip_path = f"cloned_sites/{zip_filename}"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.clone_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.clone_directory)
                    zipf.write(file_path, arcname)

        # Remover diretório temporário
        import shutil
        shutil.rmtree(self.clone_directory)

        return zip_path

    def _generate_report(self, original_url, zip_path):
        """Gera relatório da clonagem"""
        total_size_mb = self.clone_stats['total_size'] / (1024 * 1024)

        return {
            'success': True,
            'original_url': original_url,
            'zip_file': zip_path,
            'zip_size_mb': round(os.path.getsize(zip_path) / (1024 * 1024), 2),
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
                'failed_downloads': self.clone_stats['failed_downloads']
            },
            'failed_urls': self.failed_downloads[:10] if self.failed_downloads else []
        }

def clone_website_professional(url, output_name=None, max_depth=2):
    """Função principal para clonagem profissional de sites"""
    cloner = ProfessionalWebsiteCloner()
    return cloner.clone_website(url, output_name, max_depth)

# Exemplo de uso
if __name__ == "__main__":
    url = input("Digite a URL do site para clonar: ")

    print("🚀 Iniciando clonagem profissional...")
    cloner = ProfessionalWebsiteCloner()
    result = cloner.clone_website(url, max_depth=2)

    if result.get('success'):
        print("\n" + "="*80)
        print("✅ CLONAGEM CONCLUÍDA COM SUCESSO!")
        print("="*80)
        print(f"📁 Arquivo ZIP: {result['zip_file']}")
        print(f"📊 Tamanho: {result['zip_size_mb']} MB")
        print(f"📄 Arquivos HTML: {result['statistics']['html_files']}")
        print(f"🎨 Arquivos CSS: {result['statistics']['css_files']}")
        print(f"⚡ Arquivos JS: {result['statistics']['js_files']}")
        print(f"🖼️ Imagens: {result['statistics']['images']}")
        print(f"🔤 Fontes: {result['statistics']['fonts']}")
        print(f"📁 Outros: {result['statistics']['other_files']}")
        print(f"❌ Falhas: {result['statistics']['failed_downloads']}")
    else:
        print(f"❌ Erro: {result.get('error')}")
