import content from '../../config/content.json';

export default function IntroText() {
  return (
    <section className="intro-text">
      <div className="container">
        <p>
          {content.inicio.intro}
        </p>
      </div>
    </section>
  );
}