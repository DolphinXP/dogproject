import {Component, inject, signal, ViewChild} from '@angular/core';
import {DataView} from 'primeng/dataview';
import {CommonModule, NgClass} from '@angular/common';
import {MainService} from '../../service/main.service';
import {DetectInfo} from '../../domain/detect-info';
import {PreviewDialogComponent} from '../preview-dialog/preview-dialog.component';

@Component({
  selector: 'app-compact-list',
  imports: [
    CommonModule,
    DataView,
    NgClass,
    PreviewDialogComponent
  ],
  templateUrl: './compact-list.component.html',
  styleUrl: './compact-list.component.css'
})
export class CompactListComponent {
  @ViewChild(PreviewDialogComponent) previewDialog!: PreviewDialogComponent;

  detects = signal<DetectInfo[]>([]);
  mainService = inject(MainService);

  ngOnInit() {
    this.mainService.detectedCompactWebSocket((data: DetectInfo[]) => {
      // console.log('Received data:', data);
      this.detects.set(data);

    });
  }

  onItemClick(item: DetectInfo) {
    console.log('Item clicked:', item);
    this.previewDialog.showDialog(item)
  }
}
