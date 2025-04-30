import {Component, ElementRef, inject, ViewChild} from '@angular/core';
import {Router} from '@angular/router';
import {VisService} from '../service/vis.service';
import {IrService} from '../service/ir.service';
import {ConfirmationService, MessageService} from 'primeng/api';
import {ConfirmDialog} from 'primeng/confirmdialog';

@Component({
  selector: 'app-footer',
  imports: [
    ConfirmDialog
  ],
  providers: [MessageService, ConfirmationService],
  templateUrl: './footer.component.html',
  styleUrl: './footer.component.css'
})
export class FooterComponent {
  @ViewChild('startStreamButton') startStreamButton!: ElementRef;

  private router = inject(Router);
  private visService = inject(VisService);
  private irService = inject(IrService);
  private msgService = inject(MessageService);
  private confrimService = inject(ConfirmationService);

  enableStartStreamButton(enable: boolean) {
    this.startStreamButton.nativeElement.disabled = !enable;
    if (enable) {
      this.startStreamButton.nativeElement.classList.remove('button-disabled');
    } else {
      this.startStreamButton.nativeElement.classList.add('button-disabled');
    }
  }

  onStartStreamClick() {
    this.enableStartStreamButton(false);
    this.visService.connectToStream().then(value => {
      if (value && !value.success) {
        this.msgService.add({severity: 'error', summary: 'Error', detail: '连接失败，请检查网络或服务器状态'});
        this.enableStartStreamButton(true);
      }
    });
    this.irService.connectToStream().then(value => {
    });

  }

  onStopStreamClick(event: Event) {
    this.confrimService.confirm({
      target: event.target as EventTarget,
      message: '关闭会断开当前连接，是否继续？',
      header: '关闭确认',
      closable: true,
      closeOnEscape: true,
      icon: 'pi pi-exclamation-triangle',
      rejectButtonProps: {

        label: '取消',
        severity: 'secondary',
        outlined: true,
      },
      acceptButtonProps: {
        label: '确定',
      },
      accept: () => {
        this.visService.closeConnection();
        this.irService.closeConnection();
        this.enableStartStreamButton(true);
      },
      reject: () => {
        // Do nothing
      }
    });
  }


  onHomeClick() {
    this.router.navigate(['/']).then(r => console.log(r));
  }

  onTestClick() {
    this.router.navigate(['test']).then(r => console.log(r));
  }
}
