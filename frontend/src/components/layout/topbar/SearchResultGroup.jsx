import SearchResultItem from "./SearchResultItem";

export default function SearchResultGroup({ title, items, priceKey, onSelect }) {
  if (items.length === 0) return null;

  return (
    <div className="tb-search-group">
      <div className="tb-search-group-title">{title}</div>
      {items.map((item) => (
        <SearchResultItem key={item.id} item={item} priceKey={priceKey} onSelect={onSelect} />
      ))}
    </div>
  );
}