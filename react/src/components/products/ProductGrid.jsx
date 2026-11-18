import ProductCard from './ProductCard';

export default function ProductGrid({ products, onProductClick, allowAddToCart = true, getProductUrl = null }) {
  return (
    <section className="product-grid">
      {products.map((product) => (
        <ProductCard
          key={product.product_id}
          product={product}
          onProductClick={onProductClick}
          allowAddToCart={allowAddToCart}
          productUrl={typeof getProductUrl === 'function' ? getProductUrl(product) : null}
        />
      ))}
    </section>
  );
}
