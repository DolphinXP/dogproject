import {Component} from '@angular/core';
import {VisViewComponent} from '../vis-view/vis-view.component';
import {FooterComponent} from '../footer/footer.component';
import {CompactListComponent} from '../compact-list/compact-list.component';

@Component({
  selector: 'app-root',
  imports: [VisViewComponent, FooterComponent, CompactListComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  title = 'dogweb';
}
