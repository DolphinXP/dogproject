import {Component} from '@angular/core';
import {Dialog} from 'primeng/dialog';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';

@Component({
  selector: 'app-location-view-dialog',
  imports: [
    Dialog,
    FormsModule,
    ReactiveFormsModule
  ],
  templateUrl: './location-view-dialog.component.html',
  styleUrl: './location-view-dialog.component.css'
})
export class LocationViewDialogComponent {
  visible: boolean = false;

  showDialog() {
    this.visible = true;
  }
}
