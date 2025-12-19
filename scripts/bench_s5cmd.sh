#!/bin/bash

echo "========================================================"
echo "TESTE DE VELOCIDADE: s5cmd no Cloudflare R2"
echo "RTX 5090 - Ontario - 4.9 Gbps"
echo "========================================================"

# 1. Instalar s5cmd (Go)
echo ""
echo "1. Instalando s5cmd..."
curl -L -o s5cmd.tar.gz https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz
tar -xzf s5cmd.tar.gz
mv s5cmd /usr/local/bin/
chmod +x /usr/local/bin/s5cmd
s5cmd version

# 2. Configurar credenciais
echo ""
echo "2. Configurando credenciais R2..."
mkdir -p ~/.aws
cat > ~/.aws/credentials <<EOF
[default]
aws_access_key_id = f0a6f424064e46c903c76a447f5e73d2
aws_secret_access_key = 1dcf325fe8556fca221cf8b383e277e7af6660a246148d5e11e4fc67e822c9b5
EOF

cat > ~/.aws/config <<EOF
[default]
region = auto
EOF

export S3_ENDPOINT_URL="https://142ed673a5cc1a9e91519c099af3d791.r2.cloudflarestorage.com"
export S5CMD_MEM=1024 # Buffer memory for s5cmd

# 3. Gerar arquivo de teste (2GB random)
echo ""
echo "3. Gerando arquivo de teste (2GB)..."
dd if=/dev/urandom of=/tmp/test_2gb.bin bs=64M count=32 status=progress

# 4. Upload com s5cmd
echo ""
echo "4. Teste de UPLOAD (s5cmd)..."
start=$(date +%s.%N)
# --concurrency 32 = 32 threads paralelas
s5cmd --endpoint-url $S3_ENDPOINT_URL cp --concurrency 32 /tmp/test_2gb.bin s3://musetalk/speedtest/test_2gb.bin
end=$(date +%s.%N)
runtime=$(echo "$end - $start" | bc)
speed=$(echo "2048 / $runtime" | bc)
echo "   Tempo: ${runtime}s"
echo "   Velocidade: ${speed} MB/s"

# Limpar local
rm /tmp/test_2gb.bin
sync

# 5. Download com s5cmd (O MOMENTO DA VERDADE)
echo ""
echo "5. Teste de DOWNLOAD (s5cmd)..."
start=$(date +%s.%N)
# Download para /dev/null/test_2gb.bin (no disco local)
s5cmd --endpoint-url $S3_ENDPOINT_URL cp --concurrency 64 s3://musetalk/speedtest/test_2gb.bin /tmp/download_test.bin
end=$(date +%s.%N)
runtime=$(echo "$end - $start" | bc)
speed=$(echo "2048 / $runtime" | bc)

echo ""
echo "RESULTADOS FINAIS DE DOWNLOAD (s5cmd):"
echo "--------------------------------------"
echo "Tempo:       ${runtime}s"
echo "Velocidade:  ${speed} MB/s"
echo "Gigabits:    $(echo "$speed * 8 / 1024" | bc) Gbps"

# Limpar R2
echo ""
echo "Limpeza..."
s5cmd --endpoint-url $S3_ENDPOINT_URL rm s3://musetalk/speedtest/test_2gb.bin
rm /tmp/download_test.bin
echo "Done."
