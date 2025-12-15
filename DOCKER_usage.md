
## Docker Usage

### Build Locally
```bash
docker build -t rapidrar .
```

### Run Locally
```bash
docker run -d -p 8000:8000 rapidrar
```

### API Usage
The API is available at `http://localhost:8000`.

**Crack a RAR file:**
```bash
curl -X POST "http://localhost:8000/crack" \
  -F "file=@/path/to/encrypted.rar" \
  -F "min_length=1" \
  -F "max_length=4"
```

**Health Check:**
```bash
curl http://localhost:8000/health
```

### Supported Architectures
- `linux/amd64`
- `linux/arm64`
