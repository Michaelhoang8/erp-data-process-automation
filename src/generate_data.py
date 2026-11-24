"""Create deterministic fictional ERP extracts; never reads a Business Central tenant."""
import csv, random, datetime as dt
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
def generate():
    RAW.mkdir(parents=True,exist_ok=True)
    rng=random.Random(81)
    def save(name,headers,rows):
        with (RAW/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(headers);w.writerows(rows)
    vendors=[(f'V{i:03}',f'Example Supplier {i:02}',30) for i in range(1,13)]
    items=[(f'I{i:03}',f'Industrial component {i:02}',2500+i*375,50+i*3) for i in range(1,25)]
    save('vendors',['VendorID','VendorName','PaymentTermsDays'],vendors)
    save('items',['ItemID','Description','UnitCostCents','ReorderPoint'],items)
    invoices=[];payments=[];orders=[];movements=[]
    for n in range(1,601):
        posted=dt.date(2025,1,1)+dt.timedelta(days=rng.randrange(335))
        due=posted+dt.timedelta(days=30)
        amount=rng.randrange(20000,950000)
        vendor=f'V{rng.randint(1,12):03}'
        invoice=f'INV{n:05}'
        invoices.append((invoice,vendor,posted.isoformat(),due.isoformat(),amount))
        if rng.random()<.77:
            paydate=due+dt.timedelta(days=rng.randrange(-5,35))
            if paydate<=dt.date(2025,12,31):payments.append((f'PAY{n:05}',invoice,paydate.isoformat(),amount if n%7 else amount//2))
    # A known duplicate, unknown vendor, invalid due date, and missing amount.
    invoices.extend([invoices[0],('BAD_VENDOR','V999','2025-11-01','2025-12-01',45000),('BAD_DATE','V001','2025-10-01','2025-09-01',65000),('BAD_AMOUNT','V002','2025-11-01','2025-12-01','')])
    # A payment with no invoice is separately quarantined.
    payments.append(('PAY_ORPHAN','INV_UNKNOWN','2025-12-01',12000))
    for n in range(1,361):
        created=dt.date(2025,1,1)+dt.timedelta(days=rng.randrange(335))
        promised=created+dt.timedelta(days=rng.randrange(7,22))
        vendor=f'V{rng.randint(1,12):03}'
        received=promised+dt.timedelta(days=rng.randrange(1,15) if vendor=='V003' else rng.randrange(-3,6))
        received_text='' if n%13==0 or received>dt.date(2025,12,31) else received.isoformat()
        orders.append((f'PO{n:05}',vendor,f'I{rng.randint(1,24):03}',created.isoformat(),promised.isoformat(),received_text,rng.randrange(10,101)))
    for item,desc,cost,reorder in items:
        for location in ('EDM','CAL','VAN'):
            movements.append((f'M{len(movements)+1:05}',item,location,'2025-01-01',160,'Opening'))
            for month in range(1,13):
                movements.append((f'M{len(movements)+1:05}',item,location,f'2025-{month:02}-10',rng.randrange(15,65),'Receipt'))
                movements.append((f'M{len(movements)+1:05}',item,location,f'2025-{month:02}-20',-rng.randrange(20,70),'Issue'))
    movements.append(('M_NEGATIVE','I001','EDM','2025-12-31',-600,'Adjustment'))
    save('invoices',['InvoiceID','VendorID','PostingDate','DueDate','AmountCents'],invoices)
    save('payments',['PaymentID','InvoiceID','PaymentDate','AmountCents'],payments)
    save('purchase_orders',['OrderID','VendorID','ItemID','OrderDate','PromisedDate','ReceivedDate','Quantity'],orders)
    save('inventory_movements',['MovementID','ItemID','Location','PostingDate','Quantity','MovementType'],movements)
    print('Generated synthetic ERP extracts in',RAW)
if __name__=='__main__':generate()
