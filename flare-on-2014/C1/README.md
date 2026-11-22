# C1 — Flare-On 2014

| | |
|---|---|
| **Платформа / Событие** | Flare-On 2014 |
| **Категория** | reverse |
| **Сложность** | — |
| **Статус** | done |
| **Дата решения** | 2026-11-22 |
| **Ссылка на таск** | — |

## TL;DR

Дан .NET-бинарь: байты ресурса `dat_secret` XOR-ятся байтом 41 (со сдвигом
ниблов), декодированные строки складываются в сообщение. Флаг — расшифрованный
адрес `3rmahg3rd.b0b.d0ge@flare-on.com`.

## Task-1: C1

Из декомпилированного .NET мы получаем код отвечающий за кодинг страницы и текста:
```c#
private void btnDecode_Click(object sender, EventArgs e)
{
    this.pbRoge.Image = Resources.bob_roge;
    byte[] dat_secret = Resources.dat_secret;
    string text = "";
    foreach (byte b in dat_secret)
    {
        text += (char)(((b >> 4) | (((int)b << 4) & 240)) ^ 41);
    }
    text += "\0";
    string text2 = "";
    for (int j = 0; j < text.Length; j += 2)
    {
        text2 += text[j + 1];
        text2 += text[j];
    }
    string text3 = "";
    for (int k = 0; k < text2.Length; k++)
    {
        char c = text2[k];
        text3 += (char)((byte)text2[k] ^ 102);
    }
    this.lbl_title.Text = text3;
}
```

Где `Resources.dat_secret` содержит:
```text
[0]         0xA1        byte
[1]         0xB5        byte
[2]         0x44        byte
[3]         0x84        byte
[4]         0x14        byte
[5]         0xE4        byte
[6]         0xA1        byte
[7]         0xB5        byte
[8]         0xD4        byte
[9]         0x70        byte
[10]    0xB4    byte
[11]    0x91    byte
[12]    0xB4    byte
[13]    0x70    byte
[14]    0xD4    byte
[15]    0x91    byte
[16]    0xE4    byte
[17]    0xC4    byte
[18]    0x96    byte
[19]    0xF4    byte
[20]    0x54    byte
[21]    0x84    byte
[22]    0xB5    byte
[23]    0xC4    byte
[24]    0x40    byte
[25]    0x64    byte
[26]    0x74    byte
[27]    0x70    byte
[28]    0xA4    byte
[29]    0x64    byte
[30]    0x44    byte
```

Или в строку:
```text
01BB04 A1 B5 44 84 14 E4 A1 B5 D4 70 B4 91 B4 70 D4 91 E4 C4 96 F4 54 84 B5 C4 40 64 74 70 A4 64 44                                                                                                                         ..D......p...p......T...@dtp.dD                                        
```

Затем при помощи break-points получаю исходную почту:`"3rmahg3rd.b0b.d0ge@flare-on.com\0"`

---

