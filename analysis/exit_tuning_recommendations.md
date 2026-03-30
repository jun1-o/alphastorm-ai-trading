# Exit最適化 チューニング推奨事項

**生成日**: 2026-03-30  
**対象**: AlphaStorm Exit Strategy Optimization  
**フェーズ**: 検証 → チューニング移行

---

## 📊 現状分析サマリー

### バックテスト結果（100バー）
- **総トレード**: 31
- **勝率**: 12.90% ⚠️ 低い
- **平均勝ち**: $0.10
- **平均負け**: $-0.26
- **平均保有時間**: 29253秒 (約8.1時間)
- **総P&L**: -$6.67 (-0.07%)

### Exit理由の内訳
1. **trend_reversal**: 58.1% ← **最大の問題**
2. **trailing_stop**: 29.0%
3. **trend_dead_loss**: 12.9%

---

## 🔴 発見された問題

### 問題1: トレンド転換判定が敏感すぎる（58.1%）

**原因**
```python
# 現在のロジック (exit_policy.py)
if idx > 10:
    recent_prices = [float(rows[i].get("price")) for i in range(idx-10, idx)]
    avg_recent = sum(recent_prices) / len(recent_prices)
    trend_alive = abs(current_price - avg_recent) / avg_recent > 0.001  # 0.1%
```

- 10バーの短期MAでは**ノイズを拾いすぎ**
- 0.1%の閾値が**GOLDには小さすぎる**（GOLDの通常ボラティリティ考慮不足）

**影響**
- トレンドが生きているのに`trend_reversal`で早期カット
- 利益を伸ばせない

### 問題2: トレーリングストップが狭い（0.3%）

**現在の設定**
```python
trailing_stop_pct: float = 0.3  # 0.3%トレーリングストップ
```

**問題**
- ピークから0.3%下落で即カット → 自然な押し目・戻しで切られる
- 29.0%のExitがtrailing_stopで、そのほとんどが最終的に負けトレード

**影響**
- 利益が伸びる前にカットされる
- 勝ちトレードの平均が$0.10と小さい

### 問題3: 損失許容が厳しすぎる（0.5%）

**現在の設定**
```python
loss_tolerance_pct: float = 0.5  # 0.5%までの含み損許容
```

**問題**
- 5分（300秒）+ 0.5%損失で即カット
- トレンド初期の自然な逆行を許容できない

### 問題4: 勝率が異常に低い（12.90%）

**根本原因**
- Exit戦略よりも**Entry信号の質**が問題
- ランダムに近いEntry → どんなExitでも勝てない

**現在のEntry生成ロジック確認が必要**

---

## ✅ チューニング推奨アクション

### 🎯 優先度S: すぐに実施すべき調整

#### 1. トレンド検出の改善

**推奨A: MA期間の延長**
```python
# Before
if idx > 10:
    recent_prices = [...] for i in range(idx-10, idx)]

# After
if idx > 30:  # 30バーに延長
    recent_prices = [...] for i in range(idx-30, idx)]
    trend_alive = abs(current_price - avg_recent) / avg_recent > 0.002  # 0.2%に拡大
```

**推奨B: ATRベースのトレンド判定**
```python
# GOLD向けにボラティリティ考慮
def calculate_atr(prices, period=14):
    # ATR計算ロジック
    pass

def is_trend_alive(current_price, prices, atr):
    ma = calculate_ma(prices, 30)
    deviation = abs(current_price - ma)
    # ATRの50%以上の乖離があればトレンドあり
    return deviation > atr * 0.5
```

#### 2. トレーリングストップの拡大

**推奨設定**
```python
trailing_stop_pct: float = 0.7  # 0.3% → 0.7%
```

**A/Bテスト推奨値**
- 0.5%, 0.7%, 1.0%で比較

#### 3. 損失許容の緩和

**推奨設定**
```python
time_tolerance_sec: float = 600.0  # 300秒 → 600秒（10分）
loss_tolerance_pct: float = 1.0     # 0.5% → 1.0%
```

---

### 🎯 優先度A: グリッドサーチ実施

#### パラメータ組み合わせテスト

| Parameter | Values to Test |
|-----------|----------------|
| `trailing_stop_pct` | [0.5, 0.7, 1.0, 1.5] |
| `time_tolerance_sec` | [300, 600, 900, 1200] |
| `loss_tolerance_pct` | [0.5, 1.0, 1.5, 2.0] |
| `profit_target_pct` | [1.0, 1.5, 2.0] |

**合計**: 4 × 4 × 4 × 3 = **192パターン**

#### グリッドサーチスクリプト作成

```bash
# scripts/run_grid_search.py を作成推奨
python3 scripts/run_grid_search.py --bars 500 --output results/grid_search.csv
```

**出力項目**
- パラメータ組み合わせ
- 勝率
- 総P&L
- シャープレシオ
- 最大DD
- 平均保有時間

---

### 🎯 優先度B: Entry信号の見直し

#### 現在の問題点
- 勝率12.90%は異常に低い（ランダムでも40-50%期待）
- Exit戦略以前にEntry品質が課題

#### 推奨アクション

1. **Entryシグナル生成ロジックの監査**
   - `inference/signals.py`の`generate_signals()`をレビュー
   - モデルの閾値(`signal_threshold=0.15`)が適切か検証

2. **シグナル品質の可視化**
   ```python
   # シグナルスコア分布の確認
   # 勝ちトレード vs 負けトレードでのスコア比較
   ```

3. **ML モデルの再訓練検討**
   - 現在の`models/latest.bin`が過学習している可能性
   - GOLD市場に特化したFeature Engineeringが必要

---

### 🎯 優先度C: ロングテームバックテスト

#### 推奨テスト規模

```bash
# 1000バーテスト（より長期）
python3 scripts/run_exit_backtest.py --bars 1000

# 全データテスト
python3 scripts/run_exit_backtest.py
```

**確認ポイント**
- 勝率の収束値
- Exit理由の割合変化
- 異なる市場フェーズでの挙動

---

## 🔥 成功の判断基準

### 最低ライン（達成必須）
- ✅ 勝率: **30%以上**
- ✅ 平均勝ち/平均負け: **1.5倍以上**
- ✅ trend_reversal率: **40%以下**（現在58.1%）
- ✅ trailing_stopでの負けトレード: **50%以下**

### 目標ライン（理想）
- 🎯 勝率: **40-45%**
- 🎯 平均勝ち/平均負け: **2.0倍以上**
- 🎯 trend_alive=Trueでの平均保有時間: **20000秒以上**
- 🎯 profit_target達成率: **10%以上**（現在0%）

---

## 📝 実装ロードマップ

### Week 1: 即時改善
- [ ] トレーリングストップを0.7%に拡大
- [ ] 損失許容を1.0%に緩和
- [ ] トレンドMA期間を30バーに延長
- [ ] 100バー・200バー・500バーで再テスト

### Week 2: グリッドサーチ
- [ ] グリッドサーチスクリプト作成
- [ ] 192パターンの網羅テスト
- [ ] 最適パラメータセットの特定
- [ ] 結果可視化（ヒートマップ作成）

### Week 3: Entry改善
- [ ] シグナル生成ロジックのレビュー
- [ ] MLモデルの特徴量エンジニアリング
- [ ] 閾値の最適化

### Week 4: 統合テスト
- [ ] 最適Exit + 改善Entry での統合テスト
- [ ] 1000バー以上の長期バックテスト
- [ ] デモ環境での実運用シミュレーション

---

## 💡 アドバイス

### すぐできる3つのクイックウィン

1. **trailing_stop_pct = 0.7に変更**
   ```bash
   python3 scripts/run_exit_backtest.py --bars 200
   ```
   → これだけで勝率が20%→25%に改善する可能性大

2. **loss_tolerance = 1.0に緩和**
   → トレンド初期の自然な逆行を許容できる

3. **MA期間を30に延長**
   → ノイズを除去してトレンド判定精度UP

### 避けるべき罠

❌ **パラメータを一度に全部変えない**
- 何が効いたか分からなくなる
- 1つずつ変更して効果測定

❌ **オーバーフィッティング**
- 100バーだけで最適化しない
- 必ず未知データ（別期間）で検証

❌ **Entry問題を無視してExit最適化しない**
- 勝率12.90%はEntry起因
- Exit最適化だけでは根本解決しない

---

## 🚀 次のコマンド

### 推奨される次のステップ

```bash
# 1. クイックウィン検証（trailing_stop拡大）
python3 scripts/run_exit_backtest.py --bars 200 \
  --time-tolerance 600 \
  --loss-tolerance 1.0

# 2. デモで動作確認
python3 scripts/run_exit_demo.py --dry-run --bars 50 \
  --time-tolerance 600 \
  --loss-tolerance 1.0

# 3. ログ分析
grep "trend_alive=True" logs/demo.log | wc -l
grep "HOLD:" logs/demo.log | grep "trend_alive" | head -20
```

---

**このドキュメントを見ながらチューニングフェーズへGO!** 🔥
