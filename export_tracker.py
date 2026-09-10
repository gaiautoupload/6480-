from __future__ import annotations
import csv,gzip,json,sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent; SOURCE=Path(r"D:\codex\stock1"); sys.path.insert(0,str(SOURCE/"src"))
from stock1.data_ingest.parser import date_from_filename,parse_trade_file,_read_text
PAIRS=(("6480","9203",3,3,106.5,"仁新、捷立康、源傑"),("6480","9872",4,3,40.6,"4 檔"),("6480","9B2i",5,3,41.2,"5 檔"),("6480","9216",3,2,56.0,"捷立康、源傑、昱鐳"),("9203","9B2i",3,2,55.1,"泰合、捷立康、源傑"))
def quotes(path):
 out={}
 for line in _read_text(path).splitlines():
  if not line.startswith("BODY,"):continue
  f=next(csv.reader([line[5:]]))
  try:
   if len(f)>=13 and float(f[10].replace(",","") or 0)>0:out[f[0].strip()]=(f[1].strip(),float(f[10].replace(",","")))
  except ValueError:pass
 return out
def day_data(day,trade_path,quote_path):
 cache=Path(r"D:\codex\race-consensus-lab\data\daily")/(day+".json.gz")
 local_cache=ROOT/".tmp"/(day+".json.gz")
 if not cache.exists() and local_cache.exists():cache=local_cache
 if cache.exists():
  with gzip.open(cache,"rt",encoding="utf-8") as f:data=json.load(f)
  return {(b,s):v[:2] for key,v in data["flows"].items() for b,s in [key.split("|")]},{s:(v[4],float(v[0])) for s,v in data["quotes"].items()}
 flows=defaultdict(lambda:[0,0])
 for r in parse_trade_file(trade_path):flows[(r.broker_code,r.stock_code)][0]+=r.buy_shares;flows[(r.broker_code,r.stock_code)][1]+=r.sell_shares
 bar=quotes(quote_path);local_cache.parent.mkdir(exist_ok=True)
 with gzip.open(local_cache,"wt",encoding="utf-8") as f:json.dump({"flows":{f"{b}|{s}":v for (b,s),v in flows.items()},"quotes":{s:[p,p,0,0,n] for s,(n,p) in bar.items()}},f,ensure_ascii=False)
 return flows,bar
def main():
 tf={str(date_from_filename(p)):p for p in (SOURCE/"data/raw_snapshot/trades").glob("*.csv")};qf={str(date_from_filename(p)):p for p in (SOURCE/"data/raw_snapshot/quotes").glob("*.csv")};days=sorted(tf.keys()&qf.keys());inv=defaultdict(float);tracked={};alerts=[]
 research_cutoff="2026-09-08";approved=set();events_file=Path(r"D:\codex\race-consensus-lab\reports\current_regime_v1\joint_new_position_events.csv")
 if events_file.exists():
  with events_file.open(encoding="utf-8-sig",newline="") as f:
   for row in csv.DictReader(f):
    members=set(filter(None,row.get("today_new_brokers","").split(";")))
    for a,b,*_ in PAIRS:
     if {a,b}<=members:approved.add((row["signal_date"],f"{a}-{b}",row["stock_code"]))
 for day in days:
  if day=="2026-08-31":
   for k in list(inv):
    if k[1]=="6696" and inv[k]>0:inv[k]*=10
  before=dict(inv);opened=set();flows,bar=day_data(day,tf[day],qf[day])
  for k,(buy,sell) in flows.items():
   old=inv[k];inv[k]=max(0,old+buy-sell)
   if old<=0<inv[k]:opened.add(k)
  stocks={s for _,s in opened}|{k[1] for k in tracked}
  for a,b,events,hits,ret,examples in PAIRS:
   pid=f"{a}-{b}"
   for stock in stocks:
    key=(pid,stock);raw_joint=(a,stock) in opened and (b,stock) in opened;joint=(day,pid,stock) in approved if day<=research_cutoff else raw_joint
    if key not in tracked and not joint:continue
    old=before.get((a,stock),0)+before.get((b,stock),0);new=inv[(a,stock)]+inv[(b,stock)];delta=new-old;action="建倉" if joint and (key not in tracked or old<=0) else "加碼" if delta>0 else "減碼" if delta<0<new else "出清" if old>0 and new<=0 else None
    name,price=bar.get(stock,(tracked.get(key,{}).get("stock_name",stock),tracked.get(key,{}).get("latest_price",0)));item=tracked.setdefault(key,{"pair_id":pid,"brokers":[a,b],"stock_code":stock,"stock_name":name,"first_signal_date":day,"timeline":[]});item.update({"stock_name":name,"latest_price":round(price,2),"as_of":day,"total_lots":round(new/1000,2),"market_value_wan":round(new*price/10000,2),"current_state":"出清" if new<=0 else "持有"})
    if action:
     e={"date":day,"action":action,"change_lots":round(delta/1000,2),"total_lots":round(new/1000,2)};item["timeline"].append(e);alerts.append({**e,"pair_id":pid,"stock_code":stock,"stock_name":name})
 grouped={}
 for x in tracked.values():grouped.setdefault(x["stock_code"],{"stock_code":x["stock_code"],"stock_name":x["stock_name"],"latest_price":x["latest_price"],"pairs":[]})["pairs"].append(x)
 output=ROOT/"data/pair_tracker.json";generated=datetime.now().astimezone().isoformat(timespec="seconds")
 if output.exists():
  try:
   previous=json.loads(output.read_text(encoding="utf-8"))
   if previous.get("as_of")==days[-1]:generated=previous.get("generated_at",generated)
  except (ValueError,OSError):pass
 payload={"schema_version":1,"generated_at":generated,"as_of":days[-1],"definition":"兩個指定分點在同一股票、同一交易日皆由零推估庫存轉為正庫存；同股同日彙整，觸發後永久保留追蹤。","pairs":[{"id":f"{a}-{b}","brokers":[a,b],"events":e,"hits":h,"return_pct":r,"examples":x} for a,b,e,h,r,x in PAIRS],"tracked_stocks":sorted(grouped.values(),key=lambda x:max(p["first_signal_date"] for p in x["pairs"]),reverse=True),"alerts":sorted(alerts,key=lambda x:(x["date"],x["stock_code"]),reverse=True)[:100]}
 output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps({"as_of":days[-1],"stocks":len(grouped),"alerts":len(alerts)},ensure_ascii=False))
if __name__=="__main__":main()
