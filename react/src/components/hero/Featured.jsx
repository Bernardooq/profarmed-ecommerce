import content from '../../config/content.json';
import p1Webp from '../../images/prods/p1.webp';
import p1Png from '../../images/prods/p1.png';
import p2Webp from '../../images/prods/p2.webp';
import p2Png from '../../images/prods/p2.png';
import p3Webp from '../../images/prods/p3.webp';
import p3Png from '../../images/prods/p3.png';
import p4Webp from '../../images/prods/p4.webp';
import p4Png from '../../images/prods/p4.png';

const FEATURED_IMAGES = [
  { imgWebp: p1Webp, imgFallback: p1Png },
  { imgWebp: p2Webp, imgFallback: p2Png },
  { imgWebp: p3Webp, imgFallback: p3Png },
  { imgWebp: p4Webp, imgFallback: p4Png }
];

export default function Featured() {
  const { title, items } = content.inicio.featured;

  return (
    <section className="featured-products">
      <div className="container">
        <h2 className="section-title text-center">{title}</h2>
        <div className="product-grid">
          {FEATURED_IMAGES.map((imgData, i) => {
            const textInfo = items[i] || { name: '', category: '' };
            return (
              <div className="product-card" key={i}>
                <picture>
                  <source srcSet={imgData.imgWebp} type="image/webp" />
                  <img
                    src={imgData.imgFallback}
                    alt={textInfo.name}
                    className="product-card__image"
                    loading="lazy"
                  />
                </picture>
                <div className="product-card__info">
                  <h3 className="product-card__name">{textInfo.name}</h3>
                  <p className="product-card__category">{textInfo.category}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}