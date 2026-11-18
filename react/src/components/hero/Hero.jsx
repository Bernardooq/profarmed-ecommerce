import content from '../../config/content.json';

export default function Hero() {
  const { hero } = content.inicio;

  return (
    <section className="hero">
      <div className="hero__bg-image hero__bg-image--inicio"></div>
      <div className="hero__content">
        <h1 className="hero__title">
          {hero.title}
          <span className="sr-only">{hero.srOnly}</span>
        </h1>
        <h2 className="hero__subtitle">{hero.subtitle}</h2>
      </div>
    </section>
  );
}