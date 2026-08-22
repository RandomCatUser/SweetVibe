const translations = {
            en: {
                heroTitle: "Lightning-fast CLI audio.<br>Zero bulky models.",
                downloadSub: "Ultra low footprint, instant execution",
                downloadLink: "download from GitHub",
                featureTitle: "Pure CLI power, no bloat",
                featureDesc: "No heavy AI models to download or configure. SweetVibe is optimized for maximum speed and minimal memory footprint right from your terminal.",
                moreIntegrations: "View CLI docs →",
                coreCapabilities: "Engine Performance",
                cap1: "Instant Boot",
                cap2: "Tiny Binary",
                cap3: "CLI Native",
                cap4: "Zero Models",
                viewAll: "View all benchmarks →",
                signupTitle: "Stay updated on SweetVibe CLI",
                signupLi1: "Get release notifications straight from GitHub",
                signupLi2: "Terminal optimization & shortcut guides",
                signupLi3: "Contribute to the open source core",
                signupBtn: "Subscribe updates",
                footerDocs: "Documentation",
                footerPrivacy: "Privacy"
            },
            ko: {
                heroTitle: "초고속 CLI 오디오.<br>무거운 모델 다운로드 없음.",
                downloadSub: "극도로 가벼운 용량, 즉각적인 실행",
                downloadLink: "GitHub에서 다운로드",
                featureTitle: "가볍고 강력한 순수 CLI",
                featureDesc: "복잡한 AI 모델을 다운로드할 필요가 없습니다. SweetVibe는 터미널에서 최고 속도와 최소한의 메모리로 동작하도록 최적화되어 있습니다.",
                moreIntegrations: "CLI 문서 보기 →",
                coreCapabilities: "엔진 성능",
                cap1: "즉시 부팅",
                cap2: "초경량 바이너리",
                cap3: "CLI 네이티브",
                cap4: "모델 없음",
                viewAll: "모든 벤치마크 보기 →",
                signupTitle: "SweetVibe CLI 소식 받아보기",
                signupLi1: "GitHub 릴리스 알림 수신",
                signupLi2: "터미널 최적화 및 단축키 가이드",
                signupLi3: "오픈소스 코어 기여",
                signupBtn: "구독하기",
                footerDocs: "문서",
                footerPrivacy: "개인정보처리방침"
            },
            zh: {
                heroTitle: "极速终端音频。<br>零臃肿模型负担。",
                downloadSub: "极低内存占用，即开即用",
                downloadLink: "从 GitHub 下载",
                featureTitle: "纯正命令行体验，拒绝臃肿",
                featureDesc: "无需下载或配置任何庞大的 AI 模型。SweetVibe 专为极致速度与极低内存设计，直接在您的终端中高效运行。",
                moreIntegrations: "查看 CLI 文档 →",
                coreCapabilities: "引擎性能",
                cap1: "瞬间启动",
                cap2: "超小体积",
                cap3: "终端原生",
                cap4: "零模型依赖",
                viewAll: "查看全部评测 →",
                signupTitle: "关注 SweetVibe CLI 动态",
                signupLi1: "直接获取 GitHub 版本更新通知",
                signupLi2: "终端优化与快捷键指南",
                signupLi3: "参与开源核心贡献",
                signupBtn: "订阅更新",
                footerDocs: "文档",
                footerPrivacy: "隐私"
            }
        };

        let currentLang = 'en';

        function switchLanguage(lang) {
            currentLang = lang;
            
            ['en', 'ko', 'zh'].forEach(l => {
                const btn = document.getElementById(`lang-btn-${l}`);
                if (l === lang) {
                    btn.className = "px-3 py-1 rounded-full bg-black text-white transition-all";
                } else {
                    btn.className = "px-3 py-1 rounded-full text-gray-600 hover:text-black transition-all";
                }
            });

            document.getElementById('hero-title').innerHTML = translations[lang].heroTitle;
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (translations[lang][key]) {
                    el.innerText = translations[lang][key];
                }
            });
        }

        window.addEventListener('DOMContentLoaded', () => {
            fetch('https://api.github.com/repos/RandomCatUser/SweetVibe/releases/latest')
                .then(response => response.json())
                .then(data => {
                    if (data && data.tag_name) {
                        document.getElementById('github-version-text').innerText = `SweetVibe ${data.tag_name} (CLI)`;
                        if (data.html_url) {
                            document.getElementById('github-release-link').href = data.html_url;
                        }
                    } else {
                        document.getElementById('github-version-text').innerText = 'SweetVibe v1.1.0 (CLI)';
                    }
                })
                .catch(() => {
                    document.getElementById('github-version-text').innerText = 'SweetVibe v1.1.0 (CLI)';
                });
        });

        function alertBox() {
            const msg = currentLang === 'ko' ? '구독 신청 기능이 곧 추가됩니다!' : 
                        currentLang === 'zh' ? '订阅功能即将上线！' : 
                        'Subscription feature coming soon!';
            
            const banner = document.createElement('div');
            banner.className = 'fixed bottom-6 right-6 bg-black text-white text-xs px-5 py-3 rounded-xl shadow-2xl z-50 transition-all duration-300';
            banner.innerText = msg;
            document.body.appendChild(banner);
            setTimeout(() => {
                banner.style.opacity = '0';
                setTimeout(() => banner.remove(), 300);
            }, 3000);
        }