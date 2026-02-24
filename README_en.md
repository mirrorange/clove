# Clove 🍀

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)

**The all-in-one Claude reverse proxy ✨**

[English](#) | [简体中文](./README.md)

</div>

## 🌟 What is this?

Clove is a reverse proxy tool that lets you access Claude.ai through a standard API. In simple terms, it allows various AI applications to connect to Claude!

**The biggest highlight**: Clove is the first reverse proxy to support accessing Claude's official API through OAuth authentication (the same one Claude Code uses)! This means you get the full Claude API experience, including advanced features like native system messages and prefilling.

## 🚀 Quick Start

Just three steps to get started:

### 1. Install Python

Make sure you have Python 3.13 or higher on your computer

### 2. Install Clove

```bash
pip install "clove-proxy[rnet]"
```

### 3. Launch!

```bash
clove
```

After starting, you'll see a randomly generated temporary admin key in the console. Don't forget to add your own key after logging into the admin panel!

### 4. Configure Your Account

Open your browser and go to: http://localhost:5201

Log in with the admin key from earlier, then you can add your Claude account~

## ✨ Core Features

### 🔐 Dual Mode Operation

- **OAuth Mode**: Preferred method, gives you access to all Claude API features
- **Web Proxy Mode**: Automatically switches when OAuth is unavailable, works by emulating the Claude.ai web interface

### 🎯 Outstanding Compatibility

Compared to other proxy tools (like Clewd), Clove offers exceptional compatibility:

- ✅ Full support for SillyTavern
- ✅ Works with most applications that use the Claude API
- ✅ Even supports Claude Code itself!

### 🛠️ Enhanced Features

#### For OAuth Mode

- Complete access to all Claude API features
- Native system message support
- Prefilling support
- Better performance and stability

#### For Claude.ai Web Proxy Mode

Clove handles all the differences between Claude.ai web version and the API:

- Image upload support
- Extended thinking (chain of thought) support

Even through web proxy, Clove enables features that weren't originally supported:

- Function Calling
- Stop Sequences
- Token counting (estimated)
- Non-streaming responses

Clove strives to make the Claude.ai web proxy as API-like as possible for a seamless experience across all applications.

### 🎨 Friendly Admin Interface

- Modern web management interface
- No need to edit config files
- All settings can be configured in the admin panel
- Automatic user quota and status management

### 🔄 Smart Features

- **Automatic OAuth Authentication**: Completed automatically through cookies, no manual Claude Code login needed
- **Intelligent Switching**: Automatically switches between OAuth and Claude.ai web proxy
- **Quota Management**: Automatically flags when quota is exceeded and restores when reset

## ⚠️ Limitations

### 1. Android Termux Users Note

Clove depends on `curl_cffi` to request claude.ai, but this dependency doesn't work on Termux.

**Solutions**:

- Use the version without curl_cffi: `pip install clove-proxy`
  - ✅ Access Claude API through OAuth (requires manual authentication in admin panel)
  - ❌ Cannot use web proxy features
  - ❌ Cannot auto-complete OAuth authentication
- Use a reverse proxy/mirror (like fuclaude)
  - ✅ Can use all features
  - ❌ Requires an additional server (but if you have a server for mirroring, why deploy on Termux? lol)

### 2. Tool Calling Limitations

If you're using web proxy mode, avoid connecting applications that perform **many parallel tool calls**.

- Clove needs to maintain connections with Claude.ai while waiting for tool call results
- Too many parallel calls will exhaust connections and cause failures
- OAuth mode is not affected by this limitation

### 3. Prompt Structure Limitations

When Clove uses web proxy, Claude.ai adds extra system prompts and file upload structures to your prompts. When using prompts with strict structural requirements (like RP presets):

- You can predict which method your request will use. With default settings:
  - Free accounts: All requests go through Claude.ai web proxy
  - Pro accounts: Sonnet models use Claude API, Opus models use Claude.ai web proxy
  - Max accounts: All requests use Claude API
  - With multiple accounts, Clove always prioritizes accounts with API access for the requested model
- Choose prompts compatible with your request method

## 🔧 Advanced Configuration

### Environment Variables

While most settings can be configured in the admin interface, you can also use environment variables:

```bash
# Port configuration
PORT=5201

# Admin key (auto-generated if not set)
ADMIN_API_KEYS=your-secret-key

# Claude.ai Cookie
COOKIES=sessionKey=your-session-key
```

See `.env.example` for more configuration options.

### API Usage

Once configured, you can use Clove just like the standard Claude API:

```python
import anthropic

client = anthropic.Anthropic(
    base_url="http://localhost:5201",
    api_key="your-api-key"  # Create this in the admin panel
)

response = client.messages.create(
    model="claude-opus-4-20250514",
    messages=[{"role": "user", "content": "Hello, Claude!"}],
    max_tokens=1024,
)
```

## 🤝 Contributing

Contributions are welcome! If you have great ideas or found issues:

1. Fork this project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Anthropic Claude](https://www.anthropic.com/claude) - ~~Adorable little Claude~~ Powerful AI assistant
- [Clewd](https://github.com/teralomaniac/clewd/) - The original Claude.ai reverse proxy
- [ClewdR](https://github.com/Xerxes-2/clewdr) - High-performance Claude.ai reverse proxy
- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- [Tailwind CSS](https://tailwindcss.com/) - CSS framework
- [Shadcn UI](https://ui.shadcn.com/) - Modern UI component library
- [Vite](https://vitejs.dev/) - Modern frontend build tool
- [React](https://reactjs.org/) - JavaScript library

## ⚠️ Disclaimer

This project is for learning and research purposes only. When using this project, please comply with the terms of service of the relevant services. The author is not responsible for any misuse or violations of service terms.

## 📮 Contact

If you have questions or suggestions, feel free to reach out:

- Submit an [Issue](https://github.com/mirrorange/clove/issues)
- Send a Pull Request
- Email: orange@freesia.ink

## 🌸 About Clove

Clove is a plant from the Myrtaceae family's Syzygium genus, commonly used as a spice and in traditional medicine. Clove (丁香, the spice) and lilac flowers (丁香花, Syringa) are two different plants! In this project, the name Clove is actually a blend of "Claude" and "love"!

---

<div align="center">
Made with ❤️ by 🍊
</div>
