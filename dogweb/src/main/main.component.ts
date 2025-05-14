import {Component, inject} from '@angular/core';
import {ViewVisComponent} from './view-vis/view-vis.component';
import {ViewIrComponent} from './view-ir/view-ir.component';
import {MainService} from '../service/main.service';
import {VisService} from '../service/vis.service';
import {IrService} from '../service/ir.service';
import {MessageService} from 'primeng/api';
import {ResourceUsage} from '../domain/resource-usage';
import {CompactListComponent} from './compact-list/compact-list.component';
import {NgIf} from '@angular/common';

@Component({
  selector: 'app-main',
  imports: [
    ViewVisComponent,
    ViewIrComponent,
    CompactListComponent,
    NgIf

  ],
  providers: [MessageService],
  templateUrl: './main.component.html',
  styleUrl: './main.component.css'
})
export class MainComponent {
// @ViewChild('videoBackdrop') videoBackdrop!: ElementRef<HTMLVideoElement>;

  isIrMain = false;
  viewName = "VIS";

  cpuUsage = 0;
  memoryUsage = 0;
  diskUsage = 0;

  private mainService = inject(MainService);
  private visService = inject(VisService);
  private irService = inject(IrService);
  private msgService = inject(MessageService);


  ngOnInit() {
    this.mainService.resourceUsageWebSocket((data: ResourceUsage) => {
      // console.log('Received resource usage data:', data);

      this.diskUsage = data.disk;
      this.cpuUsage = data.cpu;
      this.memoryUsage = data.memory;
    });
  }

  toggleView(event: MouseEvent) {
    const target = event.currentTarget as HTMLElement;
    if (target.classList.contains('sub-view')) {
      this.isIrMain = !this.isIrMain;
      this.viewName = this.isIrMain ? "IR" : "VIS";
    }
  }
}
