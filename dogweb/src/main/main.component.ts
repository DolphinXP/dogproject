import {Component, inject} from '@angular/core';
import {SidePanelComponent} from './side-panel/side-panel.component';
import {ViewVisComponent} from './view-vis/view-vis.component';
import {ViewIrComponent} from './view-ir/view-ir.component';
import {NgClass} from '@angular/common';
import {MainService} from '../service/main.service';
import {VisService} from '../service/vis.service';
import {IrService} from '../service/ir.service';
import {MessageService} from 'primeng/api';
import {ResourceUsage} from '../domain/resource-usage';
import {ProgressBar} from 'primeng/progressbar';

@Component({
  selector: 'app-main',
  imports: [
    SidePanelComponent,
    ViewVisComponent,
    ViewIrComponent,
    NgClass,
    ProgressBar

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
