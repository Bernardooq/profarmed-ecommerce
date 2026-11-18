import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTruckFast, faBoxOpen, faHeadset } from '@fortawesome/free-solid-svg-icons';
import content from '../../config/content.json';

const ADVANTAGES_ICONS = [
  { icon: faTruckFast },
  { icon: faBoxOpen },
  { icon: faHeadset }
];

export default function Advantages() {
  const { title, items } = content.inicio.advantages;

  return (
    <section className="advantages">
      <div className="container">
        <h2 className="section-title text-center">{title}</h2>
        <div className="advantages-grid">
          {ADVANTAGES_ICONS.map((item, index) => {
            const textInfo = items[index] || { title: '', text: '' };
            return (
              <div className="advantage-item" key={index}>
                <FontAwesomeIcon icon={item.icon} className="advantage-item__icon" />
                <h3 className="advantage-item__title">{textInfo.title}</h3>
                <p>{textInfo.text}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}