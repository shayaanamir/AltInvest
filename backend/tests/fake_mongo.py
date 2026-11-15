"""A small in-memory stand-in for the pymongo calls the price feed, seed cleanup and migration check use
(no mongomock in the image). Supports equality, $exists, $in, $nin, $ne, $or; $set and $pull; sort/limit;
bulk_write of UpdateOne upserts. Not a general MongoDB emulator."""
import copy
from types import SimpleNamespace

_MISSING = object()


def matches(doc: dict, flt: dict) -> bool:
    for key, cond in (flt or {}).items():
        if key == "$or":
            if not any(matches(doc, sub) for sub in cond):
                return False
            continue
        if key == "$and":
            if not all(matches(doc, sub) for sub in cond):
                return False
            continue
        val = doc.get(key, _MISSING)
        if isinstance(cond, dict) and any(k.startswith("$") for k in cond):
            for op, arg in cond.items():
                if op == "$exists" and (val is not _MISSING) != bool(arg):
                    return False
                if op == "$in" and (val is _MISSING or val not in arg):
                    return False
                if op == "$nin" and val is not _MISSING and val in arg:
                    return False
                if op == "$ne" and val is not _MISSING and val == arg:
                    return False
        elif val is _MISSING or val != cond:
            return False
    return True


def _project(doc, projection):
    if not projection:
        return copy.deepcopy(doc)
    keep = {k for k, v in projection.items() if v and k != "_id"}
    if not keep:
        return {k: copy.deepcopy(v) for k, v in doc.items() if projection.get(k, 1)}
    return {k: copy.deepcopy(doc[k]) for k in keep if k in doc}


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = [dict(d) for d in (docs or [])]

    def find(self, flt=None, projection=None, sort=None, limit=0):
        rows = [d for d in self.docs if matches(d, flt)]
        for field, direction in reversed(sort or []):
            rows.sort(key=lambda d: (d.get(field) is None, d.get(field)), reverse=direction < 0)
        if limit:
            rows = rows[:limit]
        return [_project(d, projection) for d in rows]

    def find_one(self, flt=None, projection=None, sort=None):
        rows = self.find(flt, projection, sort, 1)
        return rows[0] if rows else None

    def count_documents(self, flt):
        return sum(matches(d, flt) for d in self.docs)

    def distinct(self, field, flt=None):
        return sorted({d[field] for d in self.docs if field in d and matches(d, flt)})

    def delete_many(self, flt):
        keep = [d for d in self.docs if not matches(d, flt)]
        n = len(self.docs) - len(keep)
        self.docs = keep
        return SimpleNamespace(deleted_count=n)

    def _apply(self, doc, update):
        changed = False
        for k, v in update.get("$set", {}).items():
            if doc.get(k, _MISSING) != v:
                doc[k] = copy.deepcopy(v)
                changed = True
        for k, cond in update.get("$pull", {}).items():
            items = doc.get(k) or []
            kept = [i for i in items if not matches(i, cond)]
            if len(kept) != len(items):
                doc[k] = kept
                changed = True
        return changed

    def update_many(self, flt, update):
        n = sum(self._apply(d, update) for d in self.docs if matches(d, flt))
        return SimpleNamespace(modified_count=n)

    def update_one(self, flt, update, upsert=False):
        for d in self.docs:
            if matches(d, flt):
                return SimpleNamespace(modified_count=int(self._apply(d, update)), upserted_id=None)
        if upsert:
            doc = {k: v for k, v in flt.items() if not k.startswith("$")}
            self._apply(doc, update)
            self.docs.append(doc)
            return SimpleNamespace(modified_count=0, upserted_id=len(self.docs))
        return SimpleNamespace(modified_count=0, upserted_id=None)

    def bulk_write(self, ops, ordered=True):
        for op in ops:                                   # pymongo UpdateOne keeps these on private attributes
            self.update_one(op._filter, op._doc, upsert=op._upsert)
        return SimpleNamespace()


class FakeDB:
    def __init__(self, **collections):
        self._c = {name: FakeCollection(docs) for name, docs in collections.items()}

    def __getitem__(self, name):
        return self._c.setdefault(name, FakeCollection())

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]

    def list_collection_names(self):
        return [n for n, c in self._c.items() if c.docs]
