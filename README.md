# hypnomuse

hypnomuse は、ローカルの音声ファイルをスキャンして埋め込みを作成し、楽曲検索や類似曲探索を行うための Python パッケージです。

## インストール

```bash
pip install git+https://github.com/m1nt-s0da/hypnomuse.git
```

## 必要環境

- Python 3.14 以上
- 音声ファイルを扱える実行環境

## データ保存先

各コマンドは `--data-dir` でデータ保存先を指定できます。毎回指定しない場合は `HYPNOMUSE_DATA_DIR` 環境変数を設定してください。

```bash
export HYPNOMUSE_DATA_DIR="$HOME/.local/share/hypnomuse"
```

## できること

- 音声ファイルをスキャンしてインデックス化する
- タイトル / アーティスト / アルバムで楽曲を検索する
- 自然言語クエリで楽曲を検索する
- 楽曲 ID をもとに類似曲を探す
- 音声ファイルのメタデータを確認する

## 使い方

### 1. 音声ファイルを登録する

```bash
python -m hypnomuse.scan "/path/to/music/**/*" --ext mp3 flac m4a
```

`glob` には複数のパターンを渡せます。

### 2. メタデータで検索する

```bash
python -m hypnomuse.find --title "Song Title" --artist "Artist Name"
```

フリーテキスト検索もできます。

```bash
python -m hypnomuse.find "favorite live version"
```

### 3. 自然言語で検索する

```bash
python -m hypnomuse.search "lofi piano for late night"
```

### 4. 類似曲を探す

```bash
python -m hypnomuse.relative 00000000-0000-0000-0000-000000000000
```

### 5. 音声ファイルのメタ情報を確認する

```bash
python -m hypnomuse.mediainfo /path/to/file.mp3
```

## 補足

- 検索用データは `--data-dir` 配下に保存されます
- 初回の検索やスキャン時には埋め込みモデルの取得に時間がかかる場合があります
