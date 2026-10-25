# infra-3

## Description

Используя данные, полученные в ходе внешней разведки, подключитесь к VPN компании.

# Solution

Вообще когда я решал один из тасок на web я запустил фаззинг
директорий для узла `10.124.1.235` и увидел endpoint `/config`:

```text
# vpn access flag
# 260f9fe9-7efd-4125-9191-e4ba6f86c286 
client
dev tun
proto tcp
remote 10.124.1.253 443

resolv-retry infinite
nobind
persist-key
persist-tun
comp-lzo

verb 4

auth-user-pass

cipher AES-256-CBC
auth SHA512

tls-client
remote-cert-tls server

<ca>
-----BEGIN CERTIFICATE-----
MIIDQjCCAiqgAwIBAgIUS33P6xLROFgQ1Ncbcroc3G5adzwwDQYJKoZIhvcNAQEL
BQAwEzERMA8GA1UEAwwIQ2hhbmdlTWUwHhcNMjQwMjE5MTAwMzEyWhcNMzQwMjE2
MTAwMzEyWjATMREwDwYDVQQDDAhDaGFuZ2VNZTCCASIwDQYJKoZIhvcNAQEBBQAD
ggEPADCCAQoCggEBALmbETxQDOws7KX237DslO5zvIunpWF9g1KQ/apac+f4NCIe
TYJEun8rC776amshu0xxv+fDjBLU2Qemz50BHoKNHDboP+MLsXFXdEhsZ96Hpg7/
dvxpljL7szOW406w65wfrSR7hSqxGOle/+VkQBrgGg/4g4L3SAZc03ZOWYE+PgsJ
E4VF7fd32PfyJnbI788m7Cj4JhvfaFRcp+nUqRk/BfPZqKWoR+55yAqdKI4Qgk0m
7MnjXHHgBBbF4hhI/YWGBWUsbzjGfONIBe1NRRqIROYZNEhRiXgUMAX+w9RektdS
Xtpe51HiSPUQo8glJBvk/CQsV59C33C+gthZ4uUCAwEAAaOBjTCBijAdBgNVHQ4E
FgQUV/orGFxtKs6+5WuxKRb2qAdJwlAwTgYDVR0jBEcwRYAUV/orGFxtKs6+5Wux
KRb2qAdJwlChF6QVMBMxETAPBgNVBAMMCENoYW5nZU1lghRLfc/rEtE4WBDU1xty
uhzcblp3PDAMBgNVHRMEBTADAQH/MAsGA1UdDwQEAwIBBjANBgkqhkiG9w0BAQsF
AAOCAQEATQ+XQprOA2Qf4T3YSR6lX7htyG+4MzBcUAj/jkjKVRSrVIznkJJdPwUk
0UyIESFVJvUMnl7hK8RSThJFfcLo3fHLCPn8VqUqtpr1WTdIOkqoA3tzDgl+5Yy+
6v7KSwKUGRCrAoJ5U8ArJq4zCGNu77fxiGDNZzUYJwmAsr4tYDCb/VPDa+IEDcVw
zZ6g1X0X59BM710Zlgx6Ncqk8xEr1Gia+7dR1acEpIwEaW0JlJzxCqxuMjDXsyTU
XshOUUrM9czERliQY8B/AGulwiMI4uf0audphXAws/RtycQDIyjEwGgwujXM6zSh
FYWgsab5pCzx4knn67nWcMvO7Q0tpQ==
-----END CERTIFICATE-----
</ca>
setenv CLIENT_CERT 1
<tls-crypt>
#
# 2048 bit OpenVPN static key
#
-----BEGIN OpenVPN Static key V1-----
17e65ede8f6f67f5b7287941e424432f
144693b91fd0a9555a1231f286d13feb
9016c6f50a814872af3d5a5644476921
c30e75f7f89d5b59af40c6923c23378e
05733f1553fb11339be301920fda6414
9c7be4536694336e1cfa612199379354
05276636ad28d91fbbba483dc9793823
5b41e375ca36aa7ed647f90aa99a56a9
beb32a618f1ca8f6c20cb5a802419e72
9fb40fe6f41ec05162c32be24a882d05
1dc8120822c59dd7c0c5df3440e07efa
704ab928e35458dc62fe84efb565c3d9
94b743e4f21aa4fa2824fab4c4abc1b5
3fb8adc3459afbfb3a9680892b0e6848
c6cb5c9c87d4e4220523199e14bf0538
2d6b012e4abd95d50baebdde0ee67b97
-----END OpenVPN Static key V1-----
</tls-crypt>

```

В общем все еще проще чем я думал, флаг указан в первых строках конфига:
`260f9fe9-7efd-4125-9191-e4ba6f86c286`

