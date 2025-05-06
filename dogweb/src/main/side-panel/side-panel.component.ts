import {Component} from '@angular/core';
import {CompactListComponent} from '../compact-list/compact-list.component';
import {Button} from 'primeng/button';

@Component({
  selector: 'app-side-panel',
  imports: [CompactListComponent, Button],
  templateUrl: './side-panel.component.html',
  styleUrl: './side-panel.component.css'
})
export class SidePanelComponent {

}
