import pandas as pd
from typing import List, Dict, Tuple, Optional
from config import TRASH_CRITERIA, COLUMN_MAPPINGS


def find_column(df: pd.DataFrame, column_type: str) -> Optional[str]:
    possible_names = COLUMN_MAPPINGS.get(column_type, [])
    columns_set = set(df.columns)
    for name in possible_names:
        if name in columns_set:
            return name
    return None


def load_report(file_path: str) -> Tuple[Optional[pd.DataFrame], str]:
    try:
        file_lower = file_path.lower()
        if file_lower.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        elif file_lower.endswith('.csv'):
            for encoding in ['utf-8', 'cp1251', 'windows-1251']:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, sep=None, engine='python')
                    break
                except Exception:
                    continue
            else:
                return None, "Не удалось прочитать CSV файл"
        else:
            return None, "Поддерживаются только .xlsx, .xls и .csv файлы"
        
        return df, "OK"
    except Exception as e:
        return None, f"Ошибка загрузки: {str(e)}"


def analyze_placements(df: pd.DataFrame) -> Tuple[List[Dict], str]:  
    placement_col = find_column(df, "placement")
    if not placement_col:
        return [], f"Не найдена колонка с площадками. Доступные колонки: {list(df.columns)}"
    
    impressions_col = find_column(df, "impressions")
    clicks_col = find_column(df, "clicks")
    cost_col = find_column(df, "cost")
    conversions_col = find_column(df, "conversions")
    
    work_df = pd.DataFrame()
    work_df['placement'] = df[placement_col].astype(str).str.strip()
    work_df['impressions'] = pd.to_numeric(df[impressions_col], errors='coerce').fillna(0) if impressions_col else 0
    work_df['clicks'] = pd.to_numeric(df[clicks_col], errors='coerce').fillna(0) if clicks_col else 0
    work_df['cost'] = pd.to_numeric(df[cost_col], errors='coerce').fillna(0) if cost_col else 0
    work_df['conversions'] = pd.to_numeric(df[conversions_col], errors='coerce').fillna(0) if conversions_col else 0
    work_df = work_df[
        (work_df['placement'] != '') & 
        (work_df['placement'] != 'nan') &
        (work_df['impressions'] >= TRASH_CRITERIA["min_impressions"])
    ].copy()
    
    if work_df.empty:
        return [], "OK"

    work_df['ctr'] = (work_df['clicks'] / work_df['impressions'] * 100).fillna(0)

    min_impr = TRASH_CRITERIA["min_impressions"]
    max_ctr = TRASH_CRITERIA["max_ctr"]
    min_cost = TRASH_CRITERIA["min_cost_without_conv"]
    
    low_ctr = (work_df['ctr'] < max_ctr) & (work_df['impressions'] >= min_impr)
    high_cost_no_conv = (work_df['cost'] >= min_cost) & (work_df['conversions'] == 0)
    low_conv = (work_df['clicks'] > 10) & (work_df['conversions'] == 0)
    
    is_trash = low_ctr | high_cost_no_conv | low_conv
    trash_df = work_df[is_trash].copy()
    
    if trash_df.empty:
        return [], "OK"
    
    # Сортируем по расходу
    trash_df = trash_df.sort_values('cost', ascending=False)
    
    # Формируем результат
    trash_placements = []
    for row in trash_df.itertuples(index=False):
        reasons = []
        if row.ctr < max_ctr and row.impressions >= min_impr:
            reasons.append("мало кликов")
        if row.cost >= min_cost and row.conversions == 0:
            reasons.append(f"расход {row.cost:.0f} руб без конверсий")
        if row.clicks > 10 and row.conversions == 0:
            reasons.append("низкая конверсия")
        
        trash_placements.append({
            "name": row.placement,
            "impressions": int(row.impressions),
            "clicks": int(row.clicks),
            "cost": row.cost,
            "conversions": int(row.conversions),
            "reasons": reasons
        })
    
    return trash_placements, "OK"


def format_trash_report(placements: List[Dict]) -> str:
    """Форматирует отчёт о мусорных площадках"""
    if not placements:
        return "✅ Мусорных площадок не найдено!"
    
    parts = [
        f"🗑 Найдено мусорных площадок: {len(placements)}\n\n"
    ]
    
    for i, p in enumerate(placements[:50], 1):
        reasons_str = ", ".join(p["reasons"])
        parts.append(f"{i}. {p['name']}\n")
        parts.append(f"   📊 Показы: {p['impressions']} | Клики: {p['clicks']} | Расход: {p['cost']:.0f}₽\n")
        parts.append(f"   ⚠️ {reasons_str}\n\n")
    
    if len(placements) > 50:
        parts.append(f"... и ещё {len(placements) - 50} площадок\n")
    
    return "".join(parts)


def get_placements_for_copy(placements: List[Dict]) -> str:
    """Возвращает список площадок для копирования"""
    return "\n".join(p["name"] for p in placements)
