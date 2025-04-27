import {Component} from '@angular/core';
import {TopBarComponent} from '../top-bar/top-bar.component';
import {VisViewComponent} from '../vis-view/vis-view.component';
import {FooterComponent} from '../footer/footer.component';

@Component({
  selector: 'app-root',
  imports: [TopBarComponent, VisViewComponent, FooterComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  title = 'dogweb';
}
