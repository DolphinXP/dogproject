import {Component} from '@angular/core';
import {CompactListComponent} from '../compact-list/compact-list.component';

@Component({
  selector: 'app-side-panel',
  imports: [CompactListComponent],
  templateUrl: './side-panel.component.html',
  styleUrl: './side-panel.component.css'
})
export class SidePanelComponent {

}
