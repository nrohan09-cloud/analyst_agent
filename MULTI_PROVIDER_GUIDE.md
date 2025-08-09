# Multi-Provider LLM Guide

The Analyst Agent now supports **multiple LLM providers** with automatic fallback, making it flexible and resilient across different AI services.

## 🎯 Supported Providers

### OpenAI
- **Models**: `gpt-4`, `gpt-4-turbo`, `gpt-4o`, `gpt-3.5-turbo`
- **Setup**: Set `OPENAI_API_KEY` environment variable
- **Best for**: General SQL generation, reliable performance

### Anthropic (Claude)
- **Models**: Claude 3 Opus, Sonnet, Haiku (auto-mapped from OpenAI model names)
- **Setup**: Set `ANTHROPIC_API_KEY` environment variable  
- **Best for**: Complex reasoning, safety-focused applications

### Local Models
- **Models**: Any Ollama-supported model (Llama, Mistral, etc.)
- **Setup**: Install Ollama locally
- **Best for**: Privacy, cost control, offline usage

## 🚀 Quick Setup

### 1. Environment Variables

Create or update your `.env` file:

```bash
# Primary provider
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4

# OpenAI (recommended)
OPENAI_API_KEY=sk-your-openai-key-here

# Anthropic (optional, for fallback)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Other settings
DEBUG=false
API_PORT=8000
```

### 2. Install Provider Dependencies

```bash
# OpenAI (included by default)
pip install langchain-openai

# Anthropic (optional)
pip install langchain-anthropic

# Local models via Ollama (optional)
pip install langchain-community
# Then install Ollama: https://ollama.ai
```

## 🔧 Configuration Options

### Provider Priority

The system automatically uses providers in this order:
1. **Configured provider** (`DEFAULT_LLM_PROVIDER`)
2. **Available fallbacks** (based on API keys)
3. **Local models** (if Ollama is installed)

### Model Mapping

When using Anthropic, OpenAI model names are automatically mapped:

```python
# OpenAI → Anthropic mapping
"gpt-4" → "claude-3-opus-20240229"
"gpt-4-turbo" → "claude-3-sonnet-20240229"
"gpt-3.5-turbo" → "claude-3-haiku-20240307"
"gpt-4o" → "claude-3-5-sonnet-20241022"
```

## 💻 Usage Examples

### Automatic Provider Selection

```python
from analyst_agent.core.llm_factory import LLMFactory

# Uses default provider from settings
llm = LLMFactory.create_llm()
```

### Explicit Provider Selection

```python
# Force OpenAI
openai_llm = LLMFactory.create_llm(provider="openai", model="gpt-4")

# Force Anthropic  
anthropic_llm = LLMFactory.create_llm(provider="anthropic", model="gpt-4")

# Local model
local_llm = LLMFactory.create_llm(provider="local", model="llama2")
```

### Check Available Providers

```python
providers = LLMFactory.get_available_providers()
print(f"Available: {providers}")
# Output: ['openai', 'anthropic'] (based on API keys)
```

## 🔄 Automatic Fallback

The system includes **intelligent fallback logic**:

1. **Primary fails** → Try next available provider
2. **All providers fail** → Raise clear error message
3. **No API keys** → Skip unavailable providers
4. **Network issues** → Automatic retry with different provider

Example fallback flow:
```
OpenAI (primary) → Anthropic (fallback) → Local (last resort)
```

## 🛡️ Error Handling

### Graceful Degradation

```python
try:
    llm = LLMFactory.create_llm()
    result = llm.invoke("Generate SQL for user count")
except Exception as e:
    # Fallback to different provider automatically handled
    # Only fails if NO providers are available
    print(f"All LLM providers failed: {e}")
```

### Provider-Specific Errors

The system logs detailed error information:

```bash
2025-07-27 [warning] Primary provider failed, trying fallbacks provider=openai
2025-07-27 [info] Using fallback provider original=openai fallback=anthropic model=gpt-4
```

## 🧪 Testing

Run the multi-provider test:

```bash
python examples/multi_provider_test.py
```

This will:
- ✅ Detect available providers
- ✅ Test LLM instance creation
- ✅ Test SQL generation
- ✅ Test fallback logic

## 🎛️ Advanced Configuration

### Custom Provider Settings

```python
# Custom temperature and parameters
llm = LLMFactory.create_llm(
    provider="anthropic",
    model="gpt-4",
    temperature=0.1,
    max_tokens=4000
)
```

### Provider Caching

LLM instances are cached for performance:

```python
# Clear cache if needed
LLMFactory.clear_cache()
```

### Docker Configuration

Update your `docker-compose.yml`:

```yaml
services:
  analyst-agent:
    environment:
      # Multi-provider setup
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DEFAULT_LLM_PROVIDER=openai
      - DEFAULT_LLM_MODEL=gpt-4
```

## 🚨 Troubleshooting

### No Providers Available

```bash
❌ No available LLM providers. Check your API keys.
```

**Solution**: Add at least one API key to your `.env` file.

### Import Errors

```bash
❌ LLM provider library not installed: anthropic
```

**Solution**: Install the required package:
```bash
pip install langchain-anthropic
```

### Model Not Found

```bash
❌ Model 'gpt-5' not found
```

**Solution**: Use supported model names or check provider documentation.

## 📊 Cost Optimization

### Provider Selection by Cost

| Provider | Cost (approx.) | Speed | Quality |
|----------|----------------|-------|---------|
| OpenAI GPT-3.5 | $ | Fast | Good |
| OpenAI GPT-4 | $$$ | Medium | Excellent |
| Anthropic Claude | $$ | Medium | Excellent |
| Local (Ollama) | Free | Varies | Good |

### Recommendations

- **Production**: OpenAI GPT-4 (primary) + Anthropic (fallback)
- **Development**: OpenAI GPT-3.5-turbo (cost-effective)
- **Privacy-focused**: Local models only
- **High-availability**: All providers configured

## 🔮 Future Providers

The architecture supports easy addition of new providers:

- Google Gemini
- Azure OpenAI
- AWS Bedrock
- Cohere
- Custom API endpoints

---

## 🎯 Summary

✅ **Multiple providers supported** (OpenAI, Anthropic, Local)  
✅ **Automatic fallback** when primary provider fails  
✅ **Intelligent model mapping** between providers  
✅ **Environment-based configuration**  
✅ **Comprehensive error handling**  
✅ **Performance caching**  
✅ **Easy testing and validation**  

The system is now **provider-agnostic** and can adapt to any LLM service, making your analyst agent **resilient and flexible**! 🚀 